from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.models import (
    LLMModelProvider,
    LLMModelProviderCreate,
    LLMModelProviderUpdate,
    LLMModelParam,
    LLMModelParamCreate,
    HealthStatusEnum,
)
from app.services.database import DatabaseService
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ModelProviderService:
    """Model-provider association management service"""

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def get_model_providers(
        self, model_id: int, is_enabled: bool = None
    ) -> List[LLMModelProvider]:
        """Get all providers of the model"""
        return self.db_service.get_model_providers(model_id, is_enabled)

    def get_model_provider_by_ids(
        self, model_id: int, provider_id: int, is_enabled: bool = None
    ) -> Optional[LLMModelProvider]:
        """Get model-provider association by model ID and provider ID"""
        return self.db_service.get_model_provider_by_ids(
            model_id, provider_id, is_enabled
        )

    def create_model_provider(
        self, model_provider_data: LLMModelProviderCreate
    ) -> LLMModelProvider:
        """Create model-provider association"""
        return self.db_service.create_model_provider(model_provider_data)

    def update_model_provider(
        self, model_provider_id: int, model_provider_data: LLMModelProviderUpdate
    ) -> LLMModelProvider:
        """Update model-provider association"""
        return self.db_service.update_model_provider(
            model_provider_id, model_provider_data
        )

    def get_model_params(
        self, model_id: int, provider_id: Optional[int] = None, is_enabled: bool = None
    ) -> List[LLMModelParam]:
        """Get model parameters"""
        return self.db_service.get_model_params(model_id, provider_id, is_enabled)

    def get_model_param_by_key(
        self,
        model_id: int,
        provider_id: Optional[int],
        param_key: str,
        is_enabled: bool = None,
    ) -> Optional[LLMModelParam]:
        """Get model parameters by model ID, provider ID and parameter key"""
        return self.db_service.get_model_param_by_key(
            model_id, provider_id, param_key, is_enabled
        )

    def create_model_param(self, param_data: LLMModelParamCreate) -> LLMModelParam:
        """Create model parameters"""
        return self.db_service.create_model_param(param_data)

    def get_all_models_providers_batch(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get providers for multiple models in batch"""
        return self.db_service.get_all_models_providers_batch(model_ids)

    def update_provider_weight(
        self, model_name: str, provider_name: str, weight: int
    ) -> bool:
        """Update provider weight"""
        return self.db_service.update_provider_weight(model_name, provider_name, weight)

    def get_healthy_model_providers(self, model_id: int) -> List[LLMModelProvider]:
        """Get healthy model-provider associations"""
        return self.db_service.get_healthy_model_providers(model_id)

    def get_best_model_provider(self, model_id: int) -> Optional[LLMModelProvider]:
        """Get best model-provider association"""
        return self.db_service.get_best_model_provider(model_id)

    def update_model_provider_health_status(
        self,
        model_id: int,
        provider_id: int,
        health_status: str,
        response_time: float = None,
        success: bool = None,
    ) -> bool:
        """Update model-provider health status"""
        return self.db_service.update_model_provider_health_status(
            model_id, provider_id, health_status, response_time, success
        )

    def update_model_provider_metrics(
        self,
        model_id: int,
        provider_id: int,
        response_time: float,
        success: bool,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> bool:
        """Update model-provider performance metrics"""
        return self.db_service.update_model_provider_metrics(
            model_id, provider_id, response_time, success, tokens_used, cost
        )

    def increment_failure_count(self, model_id: int, provider_id: int) -> bool:
        """Increment failure count"""
        return self.db_service.increment_failure_count(model_id, provider_id)

    def reset_failure_count(self, model_id: int, provider_id: int) -> bool:
        """Reset failure count"""
        return self.db_service.reset_failure_count(model_id, provider_id)

    def get_model_provider_stats(
        self, model_id: int, provider_id: int
    ) -> Dict[str, Any]:
        """Get model-provider statistics"""
        return self.db_service.get_model_provider_stats(model_id, provider_id)

    def update_model_provider_strategy(
        self,
        model_name: str,
        provider_name: str,
        strategy: str,
        strategy_config: Dict[str, Any] = None,
        priority: int = None,
    ) -> bool:
        """Update model-provider load balancing strategy"""
        return self.db_service.update_model_provider_strategy(
            model_name, provider_name, strategy, strategy_config, priority
        )

    def get_model_provider_strategy(
        self, model_name: str, provider_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get model-provider load balancing strategy"""
        return self.db_service.get_model_provider_strategy(model_name, provider_name)

    def get_model_strategies(self, model_name: str) -> List[Dict[str, Any]]:
        """Get all provider strategies of the model"""
        return self.db_service.get_model_strategies(model_name)

    def update_model_provider_circuit_breaker(
        self,
        model_name: str,
        provider_name: str,
        enabled: bool = None,
        threshold: int = None,
        timeout: int = None,
    ) -> bool:
        """Update model-provider circuit breaker configuration"""
        return self.db_service.update_model_provider_circuit_breaker(
            model_name, provider_name, enabled, threshold, timeout
        )

    def get_available_strategies(self) -> List[str]:
        """Get all available load balancing strategies"""
        return self.db_service.get_available_strategies()

    def get_strategy_statistics(self, model_name: str = None) -> Dict[str, Any]:
        """Get strategy usage statistics"""
        return self.db_service.get_strategy_statistics(model_name)
