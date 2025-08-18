import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from collections import deque
import weakref
from ..core.adapters.base import BaseAdapter, HealthStatus
from ..core.adapters import create_adapter
from ..utils.logging_config import get_factory_logger
from .database_service import db_service

logger = get_factory_logger()


class PoolStatus(str, Enum):
    """Pool status enumeration"""

    AVAILABLE = "available"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    EXPIRED = "expired"


@dataclass
class PooledAdapter:
    """Pooled adapter with performance optimizations"""

    adapter: BaseAdapter
    provider_name: str
    model_name: str
    created_time: float
    last_used_time: float
    use_count: int
    status: PoolStatus
    health_check_time: float
    max_idle_time: float = 300.0
    max_use_count: int = 1000
    performance_score: float = 1.0  # 性能评分


class OptimizedAdapterPool:
    """High-performance adapter pool with lock-free design"""

    def __init__(self):
        # 使用多个连接池减少锁竞争
        self.pool_shards: Dict[str, List[PooledAdapter]] = {}
        self.shard_locks: Dict[str, asyncio.Lock] = {}
        self.num_shards = 16  # 分片数量

        # 性能配置
        self.max_pool_size: int = 20  # 增加池大小
        self.min_pool_size: int = 5  # 增加最小池大小
        self.cleanup_interval: float = 30.0  # 减少清理间隔
        self.health_check_interval: float = 180.0  # 减少健康检查频率

        # 异步任务
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None

        # 性能统计
        self.stats = {
            "total_requests": 0,
            "pool_hits": 0,
            "pool_misses": 0,
            "avg_response_time": 0.0,
        }

    def _get_shard_key(self, model_name: str, provider_name: str) -> str:
        """获取分片键，减少锁竞争"""
        return f"{model_name}:{provider_name}:{hash(f'{model_name}:{provider_name}') % self.num_shards}"

    async def start(self):
        """启动连接池"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("🚀 Optimized adapter pool started")

    async def stop(self):
        """停止连接池"""
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

        await self._close_all_adapters()
        logger.info("🛑 Optimized adapter pool stopped")

    async def get_adapter(
        self, model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """获取适配器实例 - 优化版本"""
        shard_key = self._get_shard_key(model_name, provider_name)

        # 获取分片锁
        if shard_key not in self.shard_locks:
            self.shard_locks[shard_key] = asyncio.Lock()

        async with self.shard_locks[shard_key]:
            # 获取或创建分片池
            if shard_key not in self.pool_shards:
                self.pool_shards[shard_key] = []
                await self._initialize_pool_shard(shard_key, model_name, provider_name)

            pool = self.pool_shards[shard_key]

            # 快速查找可用适配器
            available_adapter = await self._find_available_adapter(
                pool, model_name, provider_name
            )
            if available_adapter:
                self.stats["pool_hits"] += 1
                return available_adapter

            # 创建新适配器
            if len(pool) < self.max_pool_size:
                new_adapter = await self._create_adapter_async(
                    model_name, provider_name
                )
                if new_adapter:
                    pooled_adapter = PooledAdapter(
                        adapter=new_adapter,
                        provider_name=provider_name,
                        model_name=model_name,
                        created_time=time.time(),
                        last_used_time=time.time(),
                        use_count=1,
                        status=PoolStatus.IN_USE,
                        health_check_time=time.time(),
                    )
                    pool.append(pooled_adapter)
                    self.stats["pool_misses"] += 1
                    logger.info(f"🆕 Created new adapter: {model_name}:{provider_name}")
                    return new_adapter

            # 等待可用适配器
            return await self._wait_for_available_adapter_optimized(shard_key, pool)

    async def _find_available_adapter(
        self, pool: List[PooledAdapter], model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """快速查找可用适配器"""
        current_time = time.time()

        for pooled_adapter in pool:
            if pooled_adapter.status != PoolStatus.AVAILABLE:
                continue

            # 检查过期时间
            if (
                current_time - pooled_adapter.last_used_time
                > pooled_adapter.max_idle_time
            ):
                pooled_adapter.status = PoolStatus.EXPIRED
                continue

            # 检查使用次数
            if pooled_adapter.use_count >= pooled_adapter.max_use_count:
                pooled_adapter.status = PoolStatus.EXPIRED
                continue

            # 标记为使用中
            pooled_adapter.status = PoolStatus.IN_USE
            pooled_adapter.last_used_time = current_time
            pooled_adapter.use_count += 1

            return pooled_adapter.adapter

        return None

    async def _wait_for_available_adapter_optimized(
        self, shard_key: str, pool: List[PooledAdapter]
    ) -> Optional[BaseAdapter]:
        """优化的等待机制"""
        max_wait_time = 5.0  # 最大等待5秒
        wait_interval = 0.1  # 等待间隔100ms
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # 释放锁，让其他请求有机会获取适配器
            await asyncio.sleep(wait_interval)

            # 重新获取锁并检查
            async with self.shard_locks[shard_key]:
                available_adapter = await self._find_available_adapter(pool, "", "")
                if available_adapter:
                    return available_adapter

                # 尝试创建新适配器
                if len(pool) < self.max_pool_size:
                    new_adapter = await self._create_adapter_async("", "")
                    if new_adapter:
                        # 创建新的pooled adapter...
                        return new_adapter

        logger.warning(f"⏰ Timeout waiting for adapter in shard: {shard_key}")
        return None

    async def _create_adapter_async(
        self, model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """异步创建适配器"""
        try:
            # 使用线程池执行同步操作
            loop = asyncio.get_event_loop()
            adapter = await loop.run_in_executor(
                None, self._create_adapter_sync, model_name, provider_name
            )
            return adapter
        except Exception as e:
            logger.error(f"Failed to create adapter: {e}")
            return None

    def _create_adapter_sync(
        self, model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """同步创建适配器"""
        try:
            model = db_service.get_model_by_name(model_name)
            if not model:
                logger.error(f"Model does not exist: {model_name}")
                return None

            # 创建适配器逻辑...
            adapter = create_adapter(model_name, provider_name)
            return adapter
        except Exception as e:
            logger.error(f"Failed to create adapter synchronously: {e}")
            return None

    async def release_adapter(
        self, adapter: BaseAdapter, model_name: str, provider_name: str
    ):
        """释放适配器回池"""
        shard_key = self._get_shard_key(model_name, provider_name)

        if shard_key not in self.shard_locks:
            return

        async with self.shard_locks[shard_key]:
            if shard_key not in self.pool_shards:
                return

            pool = self.pool_shards[shard_key]

            # 查找对应的pooled adapter
            for pooled_adapter in pool:
                if pooled_adapter.adapter == adapter:
                    if pooled_adapter.status == PoolStatus.IN_USE:
                        pooled_adapter.status = PoolStatus.AVAILABLE
                        pooled_adapter.last_used_time = time.time()
                        break

    async def _cleanup_loop(self):
        """优化的清理循环"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_adapters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    async def _cleanup_expired_adapters(self):
        """清理过期适配器"""
        current_time = time.time()

        for shard_key, pool in self.pool_shards.items():
            if shard_key not in self.shard_locks:
                continue

            async with self.shard_locks[shard_key]:
                # 移除过期和不可用的适配器
                pool[:] = [
                    pooled_adapter
                    for pooled_adapter in pool
                    if (
                        current_time - pooled_adapter.last_used_time
                        <= pooled_adapter.max_idle_time
                        and pooled_adapter.use_count < pooled_adapter.max_use_count
                        and pooled_adapter.status != PoolStatus.UNHEALTHY
                    )
                ]

    async def _close_all_adapters(self):
        """关闭所有适配器"""
        for shard_key, pool in self.pool_shards.items():
            if shard_key not in self.shard_locks:
                continue

            async with self.shard_locks[shard_key]:
                for pooled_adapter in pool:
                    try:
                        if hasattr(pooled_adapter.adapter, "close"):
                            await pooled_adapter.adapter.close()
                    except Exception as e:
                        logger.error(f"Error closing adapter: {e}")

    def get_pool_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        total_adapters = sum(len(pool) for pool in self.pool_shards.values())
        available_adapters = sum(
            sum(1 for pa in pool if pa.status == PoolStatus.AVAILABLE)
            for pool in self.pool_shards.values()
        )

        return {
            "total_adapters": total_adapters,
            "available_adapters": available_adapters,
            "pool_shards": len(self.pool_shards),
            "stats": self.stats,
        }
