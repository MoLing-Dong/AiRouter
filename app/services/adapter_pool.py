import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from ..core.adapters.base import BaseAdapter, HealthStatus
from ..core.adapters import create_adapter
from ..utils.logging_config import get_factory_logger
from .database_service import db_service

# 获取日志器
logger = get_factory_logger()


class PoolStatus(str, Enum):
    """池状态枚举"""
    AVAILABLE = "available"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    EXPIRED = "expired"


@dataclass
class PooledAdapter:
    """池化的适配器"""
    adapter: BaseAdapter
    provider_name: str
    model_name: str
    created_time: float
    last_used_time: float
    use_count: int
    status: PoolStatus
    health_check_time: float
    max_idle_time: float = 300.0  # 5分钟最大空闲时间
    max_use_count: int = 1000  # 最大使用次数


class AdapterPool:
    """适配器池管理器"""

    def __init__(self):
        self.pools: Dict[str, List[PooledAdapter]] = {}  # key: "model:provider"
        self.max_pool_size: int = 10  # 每个模型-提供商组合的最大池大小
        self.min_pool_size: int = 2   # 每个模型-提供商组合的最小池大小
        self.cleanup_interval: float = 60.0  # 清理间隔（秒）
        self.health_check_interval: float = 300.0  # 健康检查间隔（秒）
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """启动适配器池"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("🔄 适配器池已启动")

    async def stop(self):
        """停止适配器池"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None

        # 关闭所有适配器
        await self._close_all_adapters()
        logger.info("🛑 适配器池已停止")

    async def get_adapter_context(self, model_name: str, provider_name: str):
        """获取适配器上下文管理器"""
        class AdapterContext:
            def __init__(self, pool, model_name, provider_name):
                self.pool = pool
                self.model_name = model_name
                self.provider_name = provider_name
                self.adapter = None

            async def __aenter__(self):
                self.adapter = await self.pool.get_adapter(self.model_name, self.provider_name)
                return self.adapter

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.adapter:
                    await self.pool.release_adapter(self.adapter, self.model_name, self.provider_name)

        return AdapterContext(self, model_name, provider_name)

    async def get_adapter(self, model_name: str, provider_name: str) -> Optional[BaseAdapter]:
        """获取适配器实例"""
        pool_key = f"{model_name}:{provider_name}"
        
        async with self._lock:
            # 获取或创建池
            if pool_key not in self.pools:
                self.pools[pool_key] = []
                await self._initialize_pool(pool_key, model_name, provider_name)

            pool = self.pools[pool_key]
            
            # 查找可用的适配器
            for pooled_adapter in pool:
                if pooled_adapter.status == PoolStatus.AVAILABLE:
                    # 检查是否过期
                    if time.time() - pooled_adapter.last_used_time > pooled_adapter.max_idle_time:
                        pooled_adapter.status = PoolStatus.EXPIRED
                        continue
                    
                    # 检查使用次数
                    if pooled_adapter.use_count >= pooled_adapter.max_use_count:
                        pooled_adapter.status = PoolStatus.EXPIRED
                        continue
                    
                    # 标记为使用中
                    pooled_adapter.status = PoolStatus.IN_USE
                    pooled_adapter.last_used_time = time.time()
                    pooled_adapter.use_count += 1
                    
                    logger.info(f"🔄 从池中获取适配器: {model_name}:{provider_name} (使用次数: {pooled_adapter.use_count})")
                    return pooled_adapter.adapter

            # 如果没有可用的适配器，尝试创建新的
            if len(pool) < self.max_pool_size:
                new_adapter = await self._create_adapter(model_name, provider_name)
                if new_adapter:
                    pooled_adapter = PooledAdapter(
                        adapter=new_adapter,
                        provider_name=provider_name,
                        model_name=model_name,
                        created_time=time.time(),
                        last_used_time=time.time(),
                        use_count=1,
                        status=PoolStatus.IN_USE,
                        health_check_time=time.time()
                    )
                    pool.append(pooled_adapter)
                    logger.info(f"🆕 创建新适配器并加入池: {model_name}:{provider_name}")
                    return new_adapter

            # 如果池已满，等待可用的适配器
            logger.warning(f"⏳ 池已满，等待可用适配器: {model_name}:{provider_name}")
            return await self._wait_for_available_adapter(pool_key)

    async def release_adapter(self, adapter: BaseAdapter, model_name: str, provider_name: str):
        """释放适配器回池"""
        pool_key = f"{model_name}:{provider_name}"
        
        async with self._lock:
            if pool_key not in self.pools:
                return

            pool = self.pools[pool_key]
            
            # 查找对应的池化适配器
            for pooled_adapter in pool:
                if pooled_adapter.adapter == adapter:
                    if pooled_adapter.status == PoolStatus.IN_USE:
                        pooled_adapter.status = PoolStatus.AVAILABLE
                        pooled_adapter.last_used_time = time.time()
                        logger.info(f"🔄 释放适配器回池: {model_name}:{provider_name} (使用次数: {pooled_adapter.use_count})")
                    break

    async def _initialize_pool(self, pool_key: str, model_name: str, provider_name: str):
        """初始化适配器池"""
        logger.info(f"🔧 初始化适配器池: {pool_key}")
        
        # 创建初始的适配器
        for _ in range(self.min_pool_size):
            adapter = await self._create_adapter(model_name, provider_name)
            if adapter:
                pooled_adapter = PooledAdapter(
                    adapter=adapter,
                    provider_name=provider_name,
                    model_name=model_name,
                    created_time=time.time(),
                    last_used_time=time.time(),
                    use_count=0,
                    status=PoolStatus.AVAILABLE,
                    health_check_time=time.time()
                )
                self.pools[pool_key].append(pooled_adapter)

    async def _create_adapter(self, model_name: str, provider_name: str) -> Optional[BaseAdapter]:
        """创建新的适配器实例"""
        try:
            # 获取模型
            model = db_service.get_model_by_name(model_name)
            if not model:
                logger.error(f"❌ 模型不存在: {model_name}")
                return None

            # 获取供应商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                logger.error(f"❌ 供应商不存在: {provider_name}")
                return None

            # 获取模型-供应商关联
            model_provider = db_service.get_model_provider_by_ids(model.id, provider.id)
            if not model_provider or not model_provider.is_enabled:
                logger.error(f"❌ 模型-供应商关联不存在或未启用: {model_name}:{provider_name}")
                return None

            # 获取API密钥
            api_key_obj = db_service.get_best_api_key(provider.id)
            if not api_key_obj:
                logger.error(f"❌ 未找到API密钥: {provider_name}")
                return None

            # 构建适配器配置
            config = {
                "name": model.name,
                "provider": provider.name,
                "base_url": provider.official_endpoint or provider.third_party_endpoint,
                "api_key": api_key_obj.api_key,
                "model": model.name,
                "weight": model_provider.weight,
                "cost_per_1k_tokens": model_provider.cost_per_1k_tokens,
                "timeout": 30,
                "retry_count": 3,
                "enabled": model_provider.is_enabled,
                "is_preferred": model_provider.is_preferred,
            }

            # 创建适配器
            adapter = create_adapter(provider.name, config)
            if adapter:
                logger.success(f"✅ 创建适配器成功: {model_name}:{provider_name}")
                return adapter
            else:
                logger.error(f"❌ 创建适配器失败: {model_name}:{provider_name}")
                return None

        except Exception as e:
            logger.exception(f"❌ 创建适配器异常: {model_name}:{provider_name} - {e}")
            return None

    async def _wait_for_available_adapter(self, pool_key: str) -> Optional[BaseAdapter]:
        """等待可用的适配器"""
        pool = self.pools[pool_key]
        max_wait_time = 30.0  # 最大等待时间30秒
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            # 检查是否有可用的适配器
            for pooled_adapter in pool:
                if pooled_adapter.status == PoolStatus.AVAILABLE:
                    pooled_adapter.status = PoolStatus.IN_USE
                    pooled_adapter.last_used_time = time.time()
                    pooled_adapter.use_count += 1
                    return pooled_adapter.adapter
            
            # 等待一段时间后重试
            await asyncio.sleep(0.1)
        
        logger.error(f"⏰ 等待适配器超时: {pool_key}")
        return None

    async def _cleanup_loop(self):
        """清理过期和不可用的适配器"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_adapters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"❌ 清理循环异常: {e}")

    async def _health_check_loop(self):
        """健康检查循环"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_adapters_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"❌ 健康检查循环异常: {e}")

    async def _cleanup_expired_adapters(self):
        """清理过期的适配器"""
        async with self._lock:
            current_time = time.time()
            removed_count = 0
            
            for pool_key, pool in list(self.pools.items()):
                # 过滤掉过期的适配器
                original_size = len(pool)
                pool[:] = [
                    pooled_adapter for pooled_adapter in pool
                    if not self._is_adapter_expired(pooled_adapter, current_time)
                ]
                
                removed_count += original_size - len(pool)
                
                # 如果池太小，添加新的适配器
                if len(pool) < self.min_pool_size:
                    model_name, provider_name = pool_key.split(":", 1)
                    for _ in range(self.min_pool_size - len(pool)):
                        adapter = await self._create_adapter(model_name, provider_name)
                        if adapter:
                            pooled_adapter = PooledAdapter(
                                adapter=adapter,
                                provider_name=provider_name,
                                model_name=model_name,
                                created_time=current_time,
                                last_used_time=current_time,
                                use_count=0,
                                status=PoolStatus.AVAILABLE,
                                health_check_time=current_time
                            )
                            pool.append(pooled_adapter)
            
            if removed_count > 0:
                logger.info(f"🧹 清理了 {removed_count} 个过期适配器")

    async def _check_all_adapters_health(self):
        """检查所有适配器的健康状态"""
        async with self._lock:
            current_time = time.time()
            
            for pool_key, pool in self.pools.items():
                for pooled_adapter in pool:
                    # 只检查可用的适配器
                    if pooled_adapter.status != PoolStatus.AVAILABLE:
                        continue
                        
                    # 检查是否需要健康检查
                    if current_time - pooled_adapter.health_check_time > self.health_check_interval:
                        try:
                            health_status = await pooled_adapter.adapter.health_check()
                            pooled_adapter.health_check_time = current_time
                            
                            if health_status == HealthStatus.UNHEALTHY:
                                pooled_adapter.status = PoolStatus.UNHEALTHY
                                logger.error(f"❌ 适配器健康检查失败: {pool_key}")
                            elif health_status == HealthStatus.HEALTHY:
                                if pooled_adapter.status == PoolStatus.UNHEALTHY:
                                    pooled_adapter.status = PoolStatus.AVAILABLE
                                    logger.success(f"✅ 适配器恢复健康: {pool_key}")
                                    
                        except Exception as e:
                            logger.exception(f"❌ 健康检查异常: {pool_key} - {e}")
                            # 不要立即标记为不健康，给一些容错机会
                            if pooled_adapter.status == PoolStatus.AVAILABLE:
                                pooled_adapter.status = PoolStatus.UNHEALTHY

    def _is_adapter_expired(self, pooled_adapter: PooledAdapter, current_time: float) -> bool:
        """检查适配器是否过期"""
        # 检查空闲时间
        if current_time - pooled_adapter.last_used_time > pooled_adapter.max_idle_time:
            return True
        
        # 检查使用次数
        if pooled_adapter.use_count >= pooled_adapter.max_use_count:
            return True
        
        # 检查状态
        if pooled_adapter.status == PoolStatus.UNHEALTHY:
            return True
        
        return False

    async def _close_all_adapters(self):
        """关闭所有适配器"""
        async with self._lock:
            for pool in self.pools.values():
                for pooled_adapter in pool:
                    try:
                        await pooled_adapter.adapter.close()
                    except Exception as e:
                        logger.info(f"❌ 关闭适配器异常: {e}")
            
            self.pools.clear()

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取池统计信息"""
        stats = {
            "total_pools": len(self.pools),
            "pools": {}
        }
        
        for pool_key, pool in self.pools.items():
            available_count = sum(1 for pa in pool if pa.status == PoolStatus.AVAILABLE)
            in_use_count = sum(1 for pa in pool if pa.status == PoolStatus.IN_USE)
            unhealthy_count = sum(1 for pa in pool if pa.status == PoolStatus.UNHEALTHY)
            expired_count = sum(1 for pa in pool if pa.status == PoolStatus.EXPIRED)
            
            stats["pools"][pool_key] = {
                "total": len(pool),
                "available": available_count,
                "in_use": in_use_count,
                "unhealthy": unhealthy_count,
                "expired": expired_count,
                "max_pool_size": self.max_pool_size,
                "min_pool_size": self.min_pool_size
            }
        
        return stats


# 全局适配器池实例
adapter_pool = AdapterPool()
