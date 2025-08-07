from typing import Dict, List
from app.core.adapters.base import BaseAdapter, HealthStatus


class HealthChecker:
    """健康检查服务 - 专门处理适配器的健康检查逻辑"""

    async def check_model_health(
        self, model_name: str, adapters: List[BaseAdapter]
    ) -> Dict[str, str]:
        """检查模型的所有适配器健康状态"""
        health_status = {}

        for adapter in adapters:
            try:
                print(f"检查适配器: {type(adapter).__name__} - {adapter.provider}")
                status = await adapter.health_check()
                print(f"健康状态: {status.value}")
                health_status[f"{model_name}:{adapter.provider}"] = status.value
            except Exception as e:
                print(f"健康检查失败: {adapter.provider} - {e}")
                health_status[f"{model_name}:{adapter.provider}"] = "unhealthy"

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
