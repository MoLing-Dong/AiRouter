
import asyncio
import time
from typing import Dict, List, Optional, Any
from enum import Enum
from . import adapter_manager as model_adapter_manager
from ..core.adapters import ChatRequest, ChatResponse
from ..core.adapters.base import HealthStatus, BaseAdapter
from fastapi import HTTPException
from .load_balancing_strategies import strategy_manager, LoadBalancingStrategy


class SmartRouter:
    """智能路由器 - 为特定模型选择最佳供应商"""

    def __init__(self):
        self.request_counters: Dict[str, int] = {}
        self.last_request_time: Dict[str, float] = {}
        self.failure_counters: Dict[str, int] = {}

    async def route_request(
        self, 
        request: ChatRequest,
        specified_provider: Optional[str] = None
    ) -> ChatResponse:
        """路由请求到最佳供应商"""
        
        # 记录请求时间
        self.last_request_time[request.model] = time.time()

        try:
            # 获取模型的所有供应商配置
            from .database_service import db_service
            model = db_service.get_model_by_name(request.model, is_enabled=True)
            if not model:
                raise Exception(f"模型 {request.model} 不存在或未启用")

            model_providers = db_service.get_model_providers(model.id, is_enabled=True)
            if not model_providers:
                raise Exception(f"模型 {request.model} 没有可用的供应商")

            # 如果指定了供应商，使用指定供应商策略
            if specified_provider:
                strategy = LoadBalancingStrategy.SPECIFIED_PROVIDER
                strategy_config = {"specified_provider": specified_provider}
            else:
                # 使用第一个供应商的策略配置（或者可以设计更复杂的策略选择逻辑）
                primary_provider = model_providers[0]
                strategy = primary_provider.load_balancing_strategy
                strategy_config = primary_provider.strategy_config or {}

            # 使用策略管理器执行请求
            response = await strategy_manager.execute_strategy(
                request, model_providers, strategy, strategy_config
            )

            # 更新成功统计
            if request.model not in self.failure_counters:
                self.failure_counters[request.model] = 0

            # 增加请求计数
            self.request_counters[request.model] = (
                self.request_counters.get(request.model, 0) + 1
            )

            return response

        except Exception as e:
            # 更新失败统计
            self.failure_counters[request.model] = (
                self.failure_counters.get(request.model, 0) + 1
            )

            raise HTTPException(status_code=503, detail=f"供应商调用失败: {str(e)}")

    async def route_with_fallback(
        self, 
        request: ChatRequest,
        preferred_provider: Optional[str] = None
    ) -> ChatResponse:
        """带故障转移的路由"""
        
        # 记录请求时间
        self.last_request_time[request.model] = time.time()

        try:
            # 获取模型的所有供应商配置
            from .database_service import db_service
            model = db_service.get_model_by_name(request.model, is_enabled=True)
            if not model:
                raise Exception(f"模型 {request.model} 不存在或未启用")

            model_providers = db_service.get_model_providers(model.id, is_enabled=True)
            if not model_providers:
                raise Exception(f"模型 {request.model} 没有可用的供应商")

            # 使用故障转移策略
            strategy_config = {"preferred_provider": preferred_provider} if preferred_provider else {}
            
            response = await strategy_manager.execute_strategy(
                request, model_providers, LoadBalancingStrategy.FALLBACK, strategy_config
            )

            # 更新成功统计
            if request.model not in self.failure_counters:
                self.failure_counters[request.model] = 0

            # 增加请求计数
            self.request_counters[request.model] = (
                self.request_counters.get(request.model, 0) + 1
            )

            return response

        except Exception as e:
            # 更新失败统计
            self.failure_counters[request.model] = (
                self.failure_counters.get(request.model, 0) + 1
            )

            raise HTTPException(status_code=503, detail=f"所有供应商都不可用: {str(e)}")

    def get_best_provider_for_model(self, model_name: str) -> Optional[str]:
        """获取模型的最佳供应商"""
        try:
            from .database_service import db_service
            best_provider = db_service.get_best_provider_for_model(model_name)
            return best_provider.name if best_provider else None
        except Exception as e:
            print(f"获取最佳供应商失败: {e}")
            return None

    def get_available_providers_for_model(self, model_name: str) -> List[Dict[str, Any]]:
        """获取模型的所有可用供应商"""
        try:
            from .database_service import db_service
            recommendations = db_service.get_provider_recommendations(model_name)
            
            if "error" in recommendations:
                return []
            
            return [
                {
                    "name": rec["provider_name"],
                    "score": rec["score"],
                    "health_status": rec["health_status"],
                    "response_time": rec["response_time"],
                    "success_rate": rec["success_rate"],
                    "cost_per_1k_tokens": rec["cost_per_1k_tokens"],
                    "recommendation": rec["recommendation"]
                }
                for rec in recommendations["recommendations"]
            ]
        except Exception as e:
            print(f"获取可用供应商失败: {e}")
            return []

    def get_routing_stats(self) -> Dict[str, Any]:
        """获取路由统计信息"""
        return {
            "request_counters": self.request_counters,
            "failure_counters": self.failure_counters,
            "last_request_time": self.last_request_time,
            "available_models": model_adapter_manager.get_available_models(),
            "strategy_info": strategy_manager.get_strategy_info(),
        }

    def reset_stats(self):
        """重置统计信息"""
        self.request_counters.clear()
        self.failure_counters.clear()
        self.last_request_time.clear()

    def get_routing_recommendations(self, model_name: str) -> Dict[str, Any]:
        """获取路由建议"""
        try:
            from .database_service import db_service
            # 获取所有可用的供应商
            model = db_service.get_model_by_name(model_name, is_enabled=True)
            if not model:
                return {"error": f"模型 {model_name} 不存在或未启用"}

            model_providers = db_service.get_model_providers(model.id, is_enabled=True)
            
            recommendations = []
            for mp in sorted(model_providers, key=lambda x: x.overall_score, reverse=True):
                provider = db_service.get_provider_by_id(mp.provider_id)
                if provider:
                    recommendations.append({
                        "provider_name": provider.name,
                        "score": mp.overall_score,
                        "health_status": mp.health_status,
                        "response_time": mp.response_time_avg,
                        "success_rate": mp.success_rate,
                        "cost_per_1k_tokens": mp.cost_per_1k_tokens,
                        "strategy": mp.load_balancing_strategy,
                        "priority": mp.priority,
                        "recommendation": self._get_routing_recommendation(mp)
                    })

            return {
                "model_name": model_name,
                "recommendations": recommendations,
                "best_provider": recommendations[0] if recommendations else None
            }

        except Exception as e:
            return {"error": f"获取路由建议失败: {str(e)}"}

    def _get_routing_recommendation(self, model_provider) -> str:
        """获取路由建议"""
        if model_provider.is_preferred:
            return "首选供应商"
        elif model_provider.health_status == "healthy" and model_provider.overall_score > 0.8:
            return "推荐使用"
        elif model_provider.health_status == "healthy":
            return "可用"
        else:
            return "备用"


# 全局路由器实例
router = SmartRouter()
