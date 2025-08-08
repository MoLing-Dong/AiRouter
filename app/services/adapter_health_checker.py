from typing import Dict, List, Optional
from app.core.adapters.base import BaseAdapter, HealthStatus
from app.services.database_service import db_service
from app.models.llm_model_provider import HealthStatusEnum
from app.utils.logging_config import get_factory_logger

# 获取日志器
logger = get_factory_logger()

class HealthChecker:
    """健康检查服务 - 专门处理适配器的健康检查逻辑"""

    async def check_model_health(
        self, model_name: str, adapters: List[BaseAdapter]
    ) -> Dict[str, str]:
        """检查模型的所有适配器健康状态"""
        health_status = {}

        for adapter in adapters:
            try:
                logger.info(f"检查适配器: {type(adapter).__name__} - {adapter.provider}")
                status = await adapter.health_check()
                logger.info(f"健康状态: {status.value}")
                health_status[f"{model_name}:{adapter.provider}"] = status.value
                
                # 更新数据库中的健康状态
                self._update_db_health_status(model_name, adapter.provider, status.value)
                
            except Exception as e:
                logger.info(f"健康检查失败: {adapter.provider} - {e}")
                health_status[f"{model_name}:{adapter.provider}"] = "unhealthy"
                
                # 更新数据库中的健康状态
                self._update_db_health_status(model_name, adapter.provider, "unhealthy")

        return health_status

    async def check_all_models(
        self, model_names: List[str], model_adapters: Dict[str, List[BaseAdapter]]
    ) -> Dict[str, str]:
        """检查所有模型的健康状态"""
        all_health_status = {}

        for model_name in model_names:
            adapters = model_adapters.get(model_name, [])
            model_health = await self.check_model_health(model_name, adapters)
            all_health_status.update(model_health)

        return all_health_status

    def get_adapter_health_score(self, adapter: BaseAdapter) -> float:
        """计算适配器的健康评分"""
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
        """根据健康状态选择最佳适配器"""
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
        """从数据库获取最佳适配器"""
        try:
            # 获取模型
            model = db_service.get_model_by_name(model_name)
            if not model:
                return None

            # 获取最佳的模型-提供商关联
            best_model_provider = db_service.get_best_model_provider(model.id)
            if not best_model_provider:
                return None

            # 获取提供商信息
            provider = db_service.get_provider_by_id(best_model_provider.provider_id)
            if not provider:
                return None

            # 获取API密钥
            api_key_obj = db_service.get_best_api_key(provider.id)
            if not api_key_obj:
                return None

            # 构建适配器配置
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

            # 根据提供商类型创建适配器
            from app.core.adapters import create_adapter
            adapter = create_adapter(provider.name, config)
            
            # 设置健康状态
            if best_model_provider.health_status == HealthStatusEnum.HEALTHY.value:
                adapter.health_status = HealthStatus.HEALTHY
            elif best_model_provider.health_status == HealthStatusEnum.DEGRADED.value:
                adapter.health_status = HealthStatus.DEGRADED
            else:
                adapter.health_status = HealthStatus.UNHEALTHY

            return adapter

        except Exception as e:
            logger.info(f"从数据库获取最佳适配器失败: {e}")
            return None

    def update_adapter_metrics_to_db(
        self, model_name: str, provider_name: str, 
        response_time: float, success: bool, tokens_used: int = 0, cost: float = 0.0
    ) -> bool:
        """更新适配器指标到数据库"""
        try:
            # 获取模型
            model = db_service.get_model_by_name(model_name)
            if not model:
                return False

            # 获取提供商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return False

            # 更新指标
            return db_service.update_model_provider_metrics(
                model.id, provider.id, response_time, success, tokens_used, cost
            )

        except Exception as e:
            logger.info(f"更新适配器指标到数据库失败: {e}")
            return False

    def get_model_provider_stats_from_db(self, model_name: str, provider_name: str) -> Dict[str, any]:
        """从数据库获取模型-提供商统计信息"""
        try:
            # 获取模型
            model = db_service.get_model_by_name(model_name)
            if not model:
                return {}

            # 获取提供商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return {}

            # 获取统计信息
            return db_service.get_model_provider_stats(model.id, provider.id)

        except Exception as e:
            logger.info(f"从数据库获取统计信息失败: {e}")
            return {}

    def _update_db_health_status(self, model_name: str, provider_name: str, health_status: str):
        """更新数据库中的健康状态"""
        try:
            # 获取模型
            model = db_service.get_model_by_name(model_name)
            if not model:
                return

            # 获取提供商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return

            # 更新健康状态
            db_service.update_model_provider_health_status(
                model.id, provider.id, health_status
            )

        except Exception as e:
            logger.info(f"更新数据库健康状态失败: {e}")

    def increment_failure_count_in_db(self, model_name: str, provider_name: str) -> bool:
        """在数据库中增加失败计数"""
        try:
            # 获取模型
            model = db_service.get_model_by_name(model_name)
            if not model:
                return False

            # 获取提供商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return False

            # 增加失败计数
            return db_service.increment_failure_count(model.id, provider.id)

        except Exception as e:
            logger.info(f"增加失败计数失败: {e}")
            return False

    def reset_failure_count_in_db(self, model_name: str, provider_name: str) -> bool:
        """在数据库中重置失败计数"""
        try:
            # 获取模型
            model = db_service.get_model_by_name(model_name)
            if not model:
                return False

            # 获取提供商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                return False

            # 重置失败计数
            return db_service.reset_failure_count(model.id, provider.id)

        except Exception as e:
            logger.info(f"重置失败计数失败: {e}")
            return False
