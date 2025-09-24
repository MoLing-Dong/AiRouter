import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from app.core.adapters.base import BaseAdapter, HealthStatus
from app.core.adapters import create_adapter
from app.utils.logging_config import get_factory_logger
from ..database.database_service import db_service

# Get logger
logger = get_factory_logger()


class PoolStatus(str, Enum):
    """Pool status enumeration"""

    AVAILABLE = "available"
    IN_USE = "in_use"
    UNHEALTHY = "unhealthy"
    EXPIRED = "expired"


@dataclass
class PooledAdapter:
    """Pooled adapter"""

    adapter: BaseAdapter
    provider_name: str
    model_name: str
    created_time: float
    last_used_time: float
    use_count: int
    status: PoolStatus
    health_check_time: float
    max_idle_time: float = 300.0  # 5 minutes max idle time
    max_use_count: int = 1000  # Max usage count


class AdapterPool:
    """Adapter pool manager"""

    def __init__(self):
        self.pools: Dict[str, List[PooledAdapter]] = {}  # key: "model:provider"
        self.max_pool_size: int = (
            10  # Max pool size for each model-provider combination
        )
        self.min_pool_size: int = 2  # Min pool size for each model-provider combination
        self.cleanup_interval: float = 60.0  # Cleanup interval (seconds)
        self.health_check_interval: float = 300.0  # Health check interval (seconds)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._health_check_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Start adapter pool"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        if self._health_check_task is None:
            self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("🔄 Adapter pool started")

    async def stop(self):
        """Stop adapter pool"""
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
        logger.info("🛑 Adapter pool stopped")

    async def get_adapter_context(self, model_name: str, provider_name: str):
        """Get adapter context manager"""

        class AdapterContext:
            def __init__(self, pool, model_name, provider_name):
                self.pool = pool
                self.model_name = model_name
                self.provider_name = provider_name
                self.adapter = None

            async def __aenter__(self):
                self.adapter = await self.pool.get_adapter(
                    self.model_name, self.provider_name
                )
                return self.adapter

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self.adapter:
                    await self.pool.release_adapter(
                        self.adapter, self.model_name, self.provider_name
                    )

        return AdapterContext(self, model_name, provider_name)

    async def get_adapter(
        self, model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """Get adapter instance"""
        pool_key = f"{model_name}:{provider_name}"

        async with self._lock:
            # Get or create pool
            if pool_key not in self.pools:
                self.pools[pool_key] = []
                await self._initialize_pool(pool_key, model_name, provider_name)

            pool = self.pools[pool_key]

            # Find available adapters
            for pooled_adapter in pool:
                if pooled_adapter.status == PoolStatus.AVAILABLE:
                    # Check if expired
                    if (
                        time.time() - pooled_adapter.last_used_time
                        > pooled_adapter.max_idle_time
                    ):
                        pooled_adapter.status = PoolStatus.EXPIRED
                        continue

                    # Check usage count
                    if pooled_adapter.use_count >= pooled_adapter.max_use_count:
                        pooled_adapter.status = PoolStatus.EXPIRED
                        continue

                    # Mark as in use
                    pooled_adapter.status = PoolStatus.IN_USE
                    pooled_adapter.last_used_time = time.time()
                    pooled_adapter.use_count += 1

                    logger.info(
                        f"🔄 Get adapter from pool: {model_name}:{provider_name} (usage count: {pooled_adapter.use_count})"
                    )
                    return pooled_adapter.adapter

            # If no available adapters, try to create new ones
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
                        health_check_time=time.time(),
                    )
                    pool.append(pooled_adapter)
                    logger.info(
                        f"🆕 Create new adapter and add to pool: {model_name}:{provider_name}"
                    )
                    return new_adapter

            # If pool is full, wait for available adapters
            logger.warning(
                f"⏳ Pool is full, waiting for available adapters: {model_name}:{provider_name}"
            )
            return await self._wait_for_available_adapter(pool_key)

    async def release_adapter(
        self, adapter: BaseAdapter, model_name: str, provider_name: str
    ):
        """Release adapter back to pool"""
        pool_key = f"{model_name}:{provider_name}"

        async with self._lock:
            if pool_key not in self.pools:
                return

            pool = self.pools[pool_key]

            # Find corresponding pooled adapter
            for pooled_adapter in pool:
                if pooled_adapter.adapter == adapter:
                    if pooled_adapter.status == PoolStatus.IN_USE:
                        pooled_adapter.status = PoolStatus.AVAILABLE
                        pooled_adapter.last_used_time = time.time()
                        logger.info(
                            f"🔄 Release adapter back to pool: {model_name}:{provider_name} (usage count: {pooled_adapter.use_count})"
                        )
                    break

    async def _initialize_pool(
        self, pool_key: str, model_name: str, provider_name: str
    ):
        """Initialize adapter pool"""
        logger.info(f"🔧 Initialize adapter pool: {pool_key}")

        # Create initial adapters
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
                    health_check_time=time.time(),
                )
                self.pools[pool_key].append(pooled_adapter)

    async def _create_adapter(
        self, model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """Create new adapter instance"""
        try:
            # Get model
            model = db_service.get_model_by_name(model_name)
            if not model:
                logger.error(f"❌ Model does not exist: {model_name}")
                return None

            # Get provider
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                logger.error(f"❌ Provider does not exist: {provider_name}")
                return None

            # Get model-provider association
            model_provider = db_service.get_model_provider_by_ids(model.id, provider.id)
            if not model_provider or not model_provider.is_enabled:
                logger.error(
                    f"❌ Model-provider association does not exist or is not enabled: {model_name}:{provider_name}"
                )
                return None

            # Get API key
            api_key_obj = db_service.get_best_api_key(provider.id)
            if not api_key_obj:
                logger.error(f"❌ API key not found: {provider_name}")
                return None

            # Build adapter configuration
            config = {
                "name": model.name,
                "provider": provider.name,
                "base_url": provider.official_endpoint or provider.third_party_endpoint,
                "api_key": api_key_obj.api_key,
                "api_key_id": api_key_obj.id,  # 添加API key ID用于用量追踪
                "model": model.name,
                "weight": model_provider.weight,
                "cost_per_1k_tokens": model_provider.cost_per_1k_tokens,
                "timeout": 30,
                "retry_count": 3,
                "enabled": model_provider.is_enabled,
                "is_preferred": model_provider.is_preferred,
            }

            # Create adapter
            adapter = create_adapter(provider.name, config)
            if adapter:
                logger.success(
                    f"✅ Create adapter successfully: {model_name}:{provider_name}"
                )
                return adapter
            else:
                logger.error(f"❌ Create adapter failed: {model_name}:{provider_name}")
                return None

        except Exception as e:
            logger.exception(
                f"❌ Create adapter exception: {model_name}:{provider_name} - {e}"
            )
            return None

    async def _wait_for_available_adapter(self, pool_key: str) -> Optional[BaseAdapter]:
        """Wait for available adapters"""
        pool = self.pools[pool_key]
        max_wait_time = 30.0  # Max wait time 30 seconds
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            # Check if there are available adapters
            for pooled_adapter in pool:
                if pooled_adapter.status == PoolStatus.AVAILABLE:
                    pooled_adapter.status = PoolStatus.IN_USE
                    pooled_adapter.last_used_time = time.time()
                    pooled_adapter.use_count += 1
                    return pooled_adapter.adapter

            # Wait for a while and try again
            await asyncio.sleep(0.1)

        logger.error(f"⏰ Wait for adapter timeout: {pool_key}")
        return None

    async def _cleanup_loop(self):
        """Clean up expired and unusable adapters"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_adapters()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"❌ Cleanup loop exception: {e}")

    async def _health_check_loop(self):
        """Health check loop"""
        while True:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._check_all_adapters_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"❌ Health check loop exception: {e}")

    async def _cleanup_expired_adapters(self):
        """Clean up expired adapters"""
        async with self._lock:
            current_time = time.time()
            removed_count = 0

            for pool_key, pool in list(self.pools.items()):
                # Filter out expired adapters
                original_size = len(pool)
                pool[:] = [
                    pooled_adapter
                    for pooled_adapter in pool
                    if not self._is_adapter_expired(pooled_adapter, current_time)
                ]

                removed_count += original_size - len(pool)

                # If pool is too small, add new adapters
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
                                health_check_time=current_time,
                            )
                            pool.append(pooled_adapter)

            if removed_count > 0:
                logger.info(f"🧹 Cleaned up {removed_count} expired adapters")

    async def _check_all_adapters_health(self):
        """Check health status for all adapters"""
        async with self._lock:
            current_time = time.time()

            for pool_key, pool in self.pools.items():
                for pooled_adapter in pool:
                    # Only check available adapters
                    if pooled_adapter.status != PoolStatus.AVAILABLE:
                        continue

                    # Check if health check is needed
                    if (
                        current_time - pooled_adapter.health_check_time
                        > self.health_check_interval
                    ):
                        try:
                            health_status = await pooled_adapter.adapter.health_check()
                            pooled_adapter.health_check_time = current_time

                            if health_status == HealthStatus.UNHEALTHY:
                                pooled_adapter.status = PoolStatus.UNHEALTHY
                                logger.error(
                                    f"❌ Adapter health check failed: {pool_key}"
                                )
                            elif health_status == HealthStatus.HEALTHY:
                                if pooled_adapter.status == PoolStatus.UNHEALTHY:
                                    pooled_adapter.status = PoolStatus.AVAILABLE
                                    logger.success(
                                        f"✅ Adapter recovered health: {pool_key}"
                                    )

                        except Exception as e:
                            logger.exception(
                                f"❌ Health check exception: {pool_key} - {e}"
                            )
                            # Don't immediately mark as unhealthy, give some tolerance
                            if pooled_adapter.status == PoolStatus.AVAILABLE:
                                pooled_adapter.status = PoolStatus.UNHEALTHY

    def _is_adapter_expired(
        self, pooled_adapter: PooledAdapter, current_time: float
    ) -> bool:
        """Check if adapter is expired"""
        # Check idle time
        if current_time - pooled_adapter.last_used_time > pooled_adapter.max_idle_time:
            return True

        # Check usage count
        if pooled_adapter.use_count >= pooled_adapter.max_use_count:
            return True

        # Check status
        if pooled_adapter.status == PoolStatus.UNHEALTHY:
            return True

        return False

    async def _close_all_adapters(self):
        """Close all adapters"""
        async with self._lock:
            for pool in self.pools.values():
                for pooled_adapter in pool:
                    try:
                        await pooled_adapter.adapter.close()
                    except Exception as e:
                        logger.info(f"❌ Close adapter exception: {e}")

            self.pools.clear()

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get pool statistics"""
        stats = {"total_pools": len(self.pools), "pools": {}}

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
                "min_pool_size": self.min_pool_size,
            }

        return stats


# Global adapter pool instance
adapter_pool = AdapterPool()
