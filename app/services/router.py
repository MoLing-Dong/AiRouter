
import asyncio
import time
from typing import Dict, List, Optional, Any
from enum import Enum
import random
from . import adapter_manager as model_adapter_manager
from ..core.adapters import ChatRequest, ChatResponse
from ..core.adapters.base import HealthStatus
from fastapi import HTTPException


class LoadBalancingStrategy(str, Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    PERFORMANCE_BASED = "performance_based"
    COST_OPTIMIZED = "cost_optimized"


class SmartRouter:
    """智能路由服务，实现负载均衡和故障转移"""

    def __init__(self):
        self.request_counters: Dict[str, int] = {}
        self.last_request_time: Dict[str, float] = {}
        self.failure_counters: Dict[str, int] = {}
        self.strategy = LoadBalancingStrategy.PERFORMANCE_BASED

    def set_strategy(self, strategy: LoadBalancingStrategy):
        """设置负载均衡策略"""
        self.strategy = strategy

    def _get_healthy_models(self, model_names: List[str]) -> List[str]:
        """获取健康的模型列表"""
        healthy_models = []
        for model_name in model_names:
            try:
                adapter = model_adapter_manager.get_best_adapter(model_name)
                if adapter and adapter.health_status == HealthStatus.HEALTHY:
                    healthy_models.append(model_name)
                else:
                    print(
                        f"路由器调试: 模型 {model_name} 不健康 (适配器: {type(adapter).__name__ if adapter else 'None'}, 状态: {adapter.health_status if adapter else 'None'})"
                    )
            except Exception as e:
                print(f"路由器调试: 检查模型 {model_name} 健康状态时出错: {e}")
                continue
        return healthy_models

    def _round_robin_select(self, model_names: List[str]) -> str:
        """轮询选择"""
        if not model_names:
            raise ValueError("没有可用的模型")

        # 获取当前请求计数最少的模型
        min_count = float("inf")
        selected_model = model_names[0]

        for model_name in model_names:
            count = self.request_counters.get(model_name, 0)
            if count < min_count:
                min_count = count
                selected_model = model_name

        self.request_counters[selected_model] = (
            self.request_counters.get(selected_model, 0) + 1
        )
        return selected_model

    def _weighted_round_robin_select(self, model_names: List[str]) -> str:
        """加权轮询选择"""
        if not model_names:
            raise ValueError("没有可用的模型")

        # 计算权重（基于性能评分）
        weights = []
        for model_name in model_names:
            try:
                adapter = model_adapter_manager.get_best_adapter(model_name)
                if adapter:
                    # 使用适配器的权重或默认权重
                    weight = getattr(adapter, "weight", 1.0)
                    weights.append((model_name, weight))
                else:
                    weights.append((model_name, 0.1))  # 默认权重
            except Exception:
                weights.append((model_name, 0.1))  # 默认权重

        # 按权重排序
        weights.sort(key=lambda x: x[1], reverse=True)

        # 选择权重最高的模型
        selected_model = weights[0][0]
        self.request_counters[selected_model] = (
            self.request_counters.get(selected_model, 0) + 1
        )
        return selected_model

    def _performance_based_select(self, model_names: List[str]) -> str:
        """基于性能选择"""
        if not model_names:
            raise ValueError("没有可用的模型")

        best_model = None
        best_score = -1

        for model_name in model_names:
            try:
                adapter = model_adapter_manager.get_best_adapter(model_name)
                if adapter:
                    # 计算性能评分（基于响应时间和成功率）
                    response_time = adapter.metrics.response_time
                    success_rate = adapter.metrics.success_rate
                    score = (1 / (response_time + 1)) * success_rate

                    if score > best_score:
                        best_score = score
                        best_model = model_name
            except Exception:
                continue

        if not best_model:
            # 如果没有找到最佳模型，使用第一个可用模型
            best_model = model_names[0]

        self.request_counters[best_model] = self.request_counters.get(best_model, 0) + 1
        return best_model

    def _cost_optimized_select(self, model_names: List[str]) -> str:
        """成本优化选择"""
        if not model_names:
            raise ValueError("没有可用的模型")

        best_model = None
        best_cost_performance = float("inf")

        for model_name in model_names:
            try:
                adapter = model_adapter_manager.get_best_adapter(model_name)
                if adapter:
                    # 计算成本性能比
                    cost_per_token = adapter.metrics.cost_per_1k_tokens / 1000
                    response_time = adapter.metrics.response_time
                    success_rate = adapter.metrics.success_rate

                    # 成本性能比 = 成本 / (成功率 * (1/响应时间))
                    if success_rate > 0 and response_time > 0:
                        cost_performance = cost_per_token / (
                            success_rate * (1 / response_time)
                        )

                        if cost_performance < best_cost_performance:
                            best_cost_performance = cost_performance
                            best_model = model_name
            except Exception:
                continue

        if not best_model:
            # 如果没有找到最佳模型，使用第一个可用模型
            best_model = model_names[0]

        self.request_counters[best_model] = self.request_counters.get(best_model, 0) + 1
        return best_model

    def select_model(self, model_names: List[str]) -> str:
        """根据策略选择模型"""
        healthy_models = self._get_healthy_models(model_names)

        if not healthy_models:
            raise ValueError("没有健康的模型可用")

        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(healthy_models)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
            return self._weighted_round_robin_select(healthy_models)
        elif self.strategy == LoadBalancingStrategy.PERFORMANCE_BASED:
            return self._performance_based_select(healthy_models)
        elif self.strategy == LoadBalancingStrategy.COST_OPTIMIZED:
            return self._cost_optimized_select(healthy_models)
        else:
            return self._round_robin_select(healthy_models)

    async def route_request(self, request: ChatRequest) -> ChatResponse:
        """路由请求到最佳提供商"""
        # 始终使用用户请求的模型
        selected_model = request.model

        # 记录请求时间
        self.last_request_time[selected_model] = time.time()

        # 获取该模型的最佳适配器
        adapter = model_adapter_manager.get_best_adapter(selected_model)

        if not adapter:
            raise HTTPException(
                status_code=503,
                detail=f"模型 '{selected_model}' 没有可用的提供商适配器",
            )

        try:
            response = await adapter.chat_completion(request)

            # 更新成功统计
            if selected_model not in self.failure_counters:
                self.failure_counters[selected_model] = 0

            return response

        except Exception as e:
            # 更新失败统计
            self.failure_counters[selected_model] = (
                self.failure_counters.get(selected_model, 0) + 1
            )

            raise HTTPException(status_code=503, detail=f"提供商调用失败: {str(e)}")

    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        return {
            "request_counters": self.request_counters,
            "failure_counters": self.failure_counters,
            "last_request_time": self.last_request_time,
            "strategy": self.strategy.value,
            "available_models": model_adapter_manager.get_available_models(),
        }

    def reset_stats(self):
        """重置统计信息"""
        self.request_counters.clear()
        self.failure_counters.clear()
        self.last_request_time.clear()


# 全局路由器实例
router = SmartRouter()
