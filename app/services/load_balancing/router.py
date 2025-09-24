import asyncio
import time
from typing import Dict, List, Optional, Any
from enum import Enum
# 延迟导入避免循环依赖
from app.core.adapters import ChatRequest, ChatResponse
from app.core.adapters.base import HealthStatus, BaseAdapter
from fastapi import HTTPException
from .load_balancing_strategies import strategy_manager, LoadBalancingStrategy
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()

class SmartRouter:
    """Smart router - Select best provider for specific model"""

    def __init__(self):
        self.request_counters: Dict[str, int] = {}
        self.last_request_time: Dict[str, float] = {}
        self.failure_counters: Dict[str, int] = {}

    async def route_request(
        self, 
        request: ChatRequest,
        specified_provider: Optional[str] = None
    ) -> ChatResponse:
        """Route request to best provider"""
        
        # Record request time
        self.last_request_time[request.model] = time.time()

        try:
            # Get all provider configurations for the model
            from ..database.database_service import db_service
            model = db_service.get_model_by_name(request.model, is_enabled=True)
            if not model:
                raise Exception(f"Model {request.model} does not exist or is not enabled")

            model_providers = db_service.get_model_providers(model.id, is_enabled=True)
            if not model_providers:
                raise Exception(f"Model {request.model} has no available providers")

            # If specified provider, use specified provider strategy
            if specified_provider:
                strategy = LoadBalancingStrategy.SPECIFIED_PROVIDER
                strategy_config = {"specified_provider": specified_provider}
            else:
                # Use strategy configuration of the first provider (or can design more complex strategy selection logic)
                primary_provider = model_providers[0]
                strategy = primary_provider.load_balancing_strategy
                strategy_config = primary_provider.strategy_config or {}

            # Use strategy manager to execute request
            response = await strategy_manager.execute_strategy(
                request, model_providers, strategy, strategy_config
            )

            # Update success statistics
            if request.model not in self.failure_counters:
                self.failure_counters[request.model] = 0

            # Increase request count
            self.request_counters[request.model] = (
                self.request_counters.get(request.model, 0) + 1
            )

            return response

        except Exception as e:
            # Update failure statistics
            self.failure_counters[request.model] = (
                self.failure_counters.get(request.model, 0) + 1
            )

            raise HTTPException(status_code=503, detail=f"Provider call failed: {str(e)}")

    async def route_with_fallback(
        self, 
        request: ChatRequest,
        preferred_provider: Optional[str] = None
    ) -> ChatResponse:
        """Route with fallback"""
        
        # Record request time
        self.last_request_time[request.model] = time.time()

        try:
            # Get all provider configurations for the model
            from ..database.database_service import db_service
            model = db_service.get_model_by_name(request.model, is_enabled=True)
            if not model:
                raise Exception(f"Model {request.model} does not exist or is not enabled")

            model_providers = db_service.get_model_providers(model.id, is_enabled=True)
            if not model_providers:
                raise Exception(f"Model {request.model} has no available providers")

            # Use fallback strategy
            strategy_config = {"preferred_provider": preferred_provider} if preferred_provider else {}
            
            response = await strategy_manager.execute_strategy(
                request, model_providers, LoadBalancingStrategy.FALLBACK, strategy_config
            )

            # Update success statistics
            if request.model not in self.failure_counters:
                self.failure_counters[request.model] = 0

            # Increase request count
            self.request_counters[request.model] = (
                self.request_counters.get(request.model, 0) + 1
            )

            return response

        except Exception as e:
            # Update failure statistics
            self.failure_counters[request.model] = (
                self.failure_counters.get(request.model, 0) + 1
            )

            raise HTTPException(status_code=503, detail=f"All providers are unavailable: {str(e)}")

    def get_best_provider_for_model(self, model_name: str) -> Optional[str]:
        """Get best provider for model"""
        try:
            from ..database.database_service import db_service
            best_provider = db_service.get_best_provider_for_model(model_name)
            return best_provider.name if best_provider else None
        except Exception as e:
            logger.info(f"Get best provider failed: {e}")
            return None

    def get_available_providers_for_model(self, model_name: str) -> List[Dict[str, Any]]:
        """Get all available providers for model"""
        try:
            from ..database.database_service import db_service
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
            logger.info(f"Get available providers failed: {e}")
            return []

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "request_counters": self.request_counters,
            "failure_counters": self.failure_counters,
            "last_request_time": self.last_request_time,
            "available_models": self._get_available_models(),
            "strategy_info": strategy_manager.get_strategy_info(),
        }

    def _get_available_models(self):
        """获取可用模型列表"""
        try:
            from ..adapters.adapter_manager import adapter_manager
            return adapter_manager.get_available_models()
        except ImportError:
            return []

    def reset_stats(self):
        """Reset statistics"""
        self.request_counters.clear()
        self.failure_counters.clear()
        self.last_request_time.clear()

    def get_routing_recommendations(self, model_name: str) -> Dict[str, Any]:
        """Get routing recommendations"""
        try:
            from ..database.database_service import db_service
            # Get all available providers
            model = db_service.get_model_by_name(model_name, is_enabled=True)
            if not model:
                return {"error": f"Model {model_name} does not exist or is not enabled"}

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
            return {"error": f"Get routing recommendations failed: {str(e)}"}

    def _get_routing_recommendation(self, model_provider) -> str:
        """Get routing recommendation"""
        if model_provider.is_preferred:
            return "Preferred provider"
        elif model_provider.health_status == "healthy" and model_provider.overall_score > 0.8:
            return "Recommended"
        elif model_provider.health_status == "healthy":
            return "Available"
        else:
            return "Backup"


# Global router instance
router = SmartRouter()
