import asyncio
from typing import Dict, List, Optional
from app.core.adapters.base import BaseAdapter, HealthStatus
from app.services.database_service import db_service
from app.models.llm_model_provider import HealthStatusEnum
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class HealthChecker:
    """Health check service - specifically handle adapter health check logic"""

    async def check_single_adapter_health(
        self, model_name: str, adapter: BaseAdapter
    ) -> tuple[str, str]:
        """Check single adapter health status"""
        try:
            logger.info(f"Checking adapter: {type(adapter).__name__} - {adapter.provider}")
            status = await adapter.health_check()
            logger.info(f"Health status: {status.value}")
            
            # 更新数据库中的健康状态
            self._update_db_health_status(model_name, adapter.provider, status.value)
            
            return f"{model_name}:{adapter.provider}", status.value
            
        except Exception as e:
            logger.info(f"Health check failed: {adapter.provider} - {e}")
            
            # 更新数据库中的健康状态
            self._update_db_health_status(model_name, adapter.provider, "unhealthy")
            
            return f"{model_name}:{adapter.provider}", "unhealthy"

    async def check_model_health(
        self, model_name: str, adapters: List[BaseAdapter]
    ) -> Dict[str, str]:
        """Check all adapter health status for the model concurrently"""
        if not adapters:
            return {}

        # 创建所有适配器的健康检查任务
        tasks = [
            self.check_single_adapter_health(model_name, adapter)
            for adapter in adapters
        ]
        
        # 并发执行所有健康检查
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 处理结果
            health_status = {}
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Health check task failed: {result}")
                    continue
                    
                if isinstance(result, tuple) and len(result) == 2:
                    key, status = result
                    health_status[key] = status
                else:
                    logger.warning(f"Unexpected health check result format: {result}")
            
            return health_status
            
        except Exception as e:
            logger.error(f"Concurrent health check failed for model {model_name}: {e}")
            # 回退到串行执行
            return await self._check_model_health_sequential(model_name, adapters)

    async def _check_model_health_sequential(
        self, model_name: str, adapters: List[BaseAdapter]
    ) -> Dict[str, str]:
        """Fallback sequential health check method"""
        health_status = {}

        for adapter in adapters:
            try:
                logger.info(f"Sequential health check: {type(adapter).__name__} - {adapter.provider}")
                status = await adapter.health_check()
                logger.info(f"Health status: {status.value}")
                health_status[f"{model_name}:{adapter.provider}"] = status.value
                
                # 更新数据库中的健康状态
                self._update_db_health_status(model_name, adapter.provider, status.value)
                
            except Exception as e:
                logger.info(f"Health check failed: {adapter.provider} - {e}")
                health_status[f"{model_name}:{adapter.provider}"] = "unhealthy"
                
                # 更新数据库中的健康状态
                self._update_db_health_status(model_name, adapter.provider, "unhealthy")

        return health_status

    async def check_all_models(
        self, model_names: List[str], model_adapters: Dict[str, List[BaseAdapter]]
    ) -> Dict[str, str]:
        """Check health status for all models concurrently"""
        if not model_names:
            return {}

        # 创建所有模型的健康检查任务
        tasks = []
        for model_name in model_names:
            adapters = model_adapters.get(model_name, [])
            if adapters:  # 只检查有适配器的模型
                task = self.check_model_health(model_name, adapters)
                tasks.append(task)

        if not tasks:
            return {}

        # 并发执行所有模型的健康检查
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 合并所有结果
            all_health_status = {}
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    model_name = model_names[i] if i < len(model_names) else "unknown"
                    logger.error(f"Health check failed for model {model_name}: {result}")
                    continue
                    
                if isinstance(result, dict):
                    all_health_status.update(result)
                else:
                    logger.warning(f"Unexpected model health check result: {result}")
            
            return all_health_status
            
        except Exception as e:
            logger.error(f"Concurrent model health check failed: {e}")
            # 回退到串行执行
            return await self._check_all_models_sequential(model_names, model_adapters)

    async def _check_all_models_sequential(
        self, model_names: List[str], model_adapters: Dict[str, List[BaseAdapter]]
    ) -> Dict[str, str]:
        """Fallback sequential health check for all models"""
        all_health_status = {}

        for model_name in model_names:
            adapters = model_adapters.get(model_name, [])
            model_health = await self._check_model_health_sequential(model_name, adapters)
            all_health_status.update(model_health)

        return all_health_status

    async def check_all_models_with_timeout(
        self, 
        model_names: List[str], 
        model_adapters: Dict[str, List[BaseAdapter]], 
        timeout: float = 30.0
    ) -> Dict[str, str]:
        """Check health status for all models with timeout"""
        try:
            # 使用超时机制执行并发健康检查
            result = await asyncio.wait_for(
                self.check_all_models(model_names, model_adapters),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Health check timeout after {timeout} seconds, falling back to sequential")
            return await self._check_all_models_sequential(model_names, model_adapters)
        except Exception as e:
            logger.error(f"Health check with timeout failed: {e}")
            return await self._check_all_models_sequential(model_names, model_adapters)

    async def check_model_health_with_timeout(
        self, 
        model_name: str, 
        adapters: List[BaseAdapter], 
        timeout: float = 10.0
    ) -> Dict[str, str]:
        """Check single model health status with timeout"""
        try:
            # 使用超时机制执行并发健康检查
            result = await asyncio.wait_for(
                self.check_model_health(model_name, adapters),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            logger.warning(f"Model health check timeout after {timeout} seconds, falling back to sequential")
            return await self._check_model_health_sequential(model_name, adapters)
        except Exception as e:
            logger.error(f"Model health check with timeout failed: {e}")
            return await self._check_model_health_sequential(model_name, adapters)

    def get_adapter_health_score(self, adapter: BaseAdapter) -> float:
        """Calculate adapter health score"""
        score = 0.0

        # 基础分数
        if adapter.health_status == HealthStatus.HEALTHY:
            score += 1.0
        elif adapter.health_status == HealthStatus.DEGRADED:
            score += 0.5
        else:
            score += 0.1

        # 考虑性能指标
        if hasattr(adapter, "metrics"):
            # 响应时间评分（越短越好）
            response_time_score = max(0, 1 - adapter.metrics.response_time / 10)
            score += response_time_score * 0.3

            # 成功率评分
            score += adapter.metrics.success_rate * 0.3

            # 成本评分（越便宜越好）
            cost_score = max(0, 1 - adapter.metrics.cost_per_1k_tokens / 0.1)
            score += cost_score * 0.2

        return score

    def get_best_adapter_by_health(self, adapters: List[BaseAdapter]) -> BaseAdapter:
        """Select best adapter based on health status"""
        if not adapters:
            return None

        best_adapter = None
        best_score = -1

        for adapter in adapters:
            score = self.get_adapter_health_score(adapter)
            if score > best_score:
                best_score = score
                best_adapter = adapter

        return best_adapter

    def get_best_adapter_from_db(self, model_name: str) -> Optional[BaseAdapter]:
        """Get best adapter from database"""
        try:
            # Get model
            model = db_service.get_model_by_name(model_name)
            if not model:
                return None

            # Get best model-provider association
            best_model_provider = db_service.get_best_model_provider(model.id)
            if not best_model_provider:
                return None

            # Get provider information
            provider = db_service.get_provider_by_id(best_model_provider.provider_id)
            if not provider:
                return None

            # Get API key
            api_key_obj = db_service.get_best_api_key(provider.id)
            if not api_key_obj:
                return None

            # Build adapter configuration
            config = {
                "name": model.name,
                "provider": provider.name,
                "base_url": provider.official_endpoint or provider.third_party_endpoint,
                "api_key": api_key_obj.api_key,
                "weight": best_model_provider.weight,
                "cost_per_1k_tokens": best_model_provider.cost_per_1k_tokens,
                "timeout": 30,
                "retry_count": 3,
                "enabled": best_model_provider.is_enabled,
                "is_preferred": best_model_provider.is_preferred,
            }

            # Create adapter based on provider type
            from app.core.adapters import create_adapter
            adapter = create_adapter(provider.name, config)
            
            # Set health status
            if best_model_provider.health_status == HealthStatusEnum.HEALTHY.value:
                adapter.health_status = HealthStatus.HEALTHY
            elif best_model_provider.health_status == HealthStatusEnum.DEGRADED.value:
                adapter.health_status = HealthStatus.DEGRADED
            else:
                adapter.health_status = HealthStatus.UNHEALTHY

            return adapter

        except Exception as e:
            logger.info(f"Failed to get best adapter from database: {e}")
            return None

    def update_adapter_metrics_to_db(
        self, model_name: str, provider_name: str, 
        response_time: float, success: bool, tokens_used: int = 0, cost: float = 0.0
    ) -> bool:
        """Update adapter metrics to database"""
        try:
            # Get model
            model = db_service.get_model_by_name(model_name)
            if not model:
                return False

            # Get provider
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return False

            # Update metrics
            return db_service.update_model_provider_metrics(
                model.id, provider.id, response_time, success, tokens_used, cost
            )

        except Exception as e:
            logger.info(f"Failed to update adapter metrics to database: {e}")
            return False

    def get_model_provider_stats_from_db(self, model_name: str, provider_name: str) -> Dict[str, any]:
        """Get model-provider statistics from database"""
        try:
            # Get model
            model = db_service.get_model_by_name(model_name)
            if not model:
                return {}

            # Get provider
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return {}

            # Get statistics
            return db_service.get_model_provider_stats(model.id, provider.id)

        except Exception as e:
            logger.info(f"Failed to get statistics from database: {e}")
            return {}

    def _update_db_health_status(self, model_name: str, provider_name: str, health_status: str):
        """Update health status in database"""
        try:
            # Get model
            model = db_service.get_model_by_name(model_name)
            if not model:
                return

            # Get provider
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return

            # Update health status
            db_service.update_model_provider_health_status(
                model.id, provider.id, health_status
            )

        except Exception as e:
            logger.info(f"Failed to update health status in database: {e}")

    def increment_failure_count_in_db(self, model_name: str, provider_name: str) -> bool:
        """Increment failure count in database"""
        try:
            # Get model
            model = db_service.get_model_by_name(model_name)
            if not model:
                return False

            # Get provider
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return False

            # Increment failure count
            return db_service.increment_failure_count(model.id, provider.id)

        except Exception as e:
            logger.info(f"Failed to increment failure count in database: {e}")
            return False

    def reset_failure_count_in_db(self, model_name: str, provider_name: str) -> bool:
        """Reset failure count in database"""
        try:
            # Get model
            model = db_service.get_model_by_name(model_name)
            if not model:
                return False

            # Get provider
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return False

            # Reset failure count
            return db_service.reset_failure_count(model.id, provider.id)

        except Exception as e:
            logger.info(f"Failed to reset failure count in database: {e}")
            return False
