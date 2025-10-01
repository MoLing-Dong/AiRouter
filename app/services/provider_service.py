from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import datetime
from ..models import (
    LLMProvider,
    LLMProviderCreate,
    LLMProviderApiKey,
    LLMProviderApiKeyCreate,
)
from .database.database_service import DatabaseService
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ProviderService:
    """Provider management service"""

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def get_provider_by_id(
        self, provider_id: int, is_enabled: bool = None
    ) -> Optional[LLMProvider]:
        """Get provider by ID"""
        return self.db_service.get_provider_by_id(provider_id, is_enabled)

    def get_provider_by_name(self, provider_name: str) -> Optional[LLMProvider]:
        """Get provider by name"""
        return self.db_service.get_provider_by_name(provider_name)

    def get_provider_by_name_and_type(
        self, provider_name: str, provider_type: str
    ) -> Optional[LLMProvider]:
        """Get provider by name and type"""
        return self.db_service.get_provider_by_name_and_type(
            provider_name, provider_type
        )

    def get_all_providers(self, is_enabled: bool = None) -> List[LLMProvider]:
        """Get all providers"""
        return self.db_service.get_all_providers(is_enabled)

    def create_provider(self, provider_data: LLMProviderCreate) -> LLMProvider:
        """Create provider"""
        return self.db_service.create_provider(provider_data)

    def get_provider_api_keys(
        self, provider_id: int, is_enabled: bool = None
    ) -> List[LLMProviderApiKey]:
        """Get all API keys of the provider"""
        return self.db_service.get_provider_api_keys(provider_id, is_enabled)

    def get_best_api_key(self, provider_id: int) -> Optional[LLMProviderApiKey]:
        """Get best API key"""
        return self.db_service.get_best_api_key(provider_id)

    def create_provider_api_key(
        self, api_key_data: LLMProviderApiKeyCreate
    ) -> LLMProviderApiKey:
        """Create provider API key"""
        return self.db_service.create_provider_api_key(api_key_data)

    def update_api_key_usage(self, apikey_id: int, usage_count: int = None) -> bool:
        """Update API key usage count"""
        return self.db_service.update_api_key_usage(apikey_id, usage_count)

    def get_provider_health_status(self, provider_name: str) -> Dict[str, Any]:
        """Get provider health status"""
        return self.db_service.get_provider_health_status(provider_name)

    def get_all_providers_with_health(self) -> List[Dict[str, Any]]:
        """Get all providers and their health status"""
        return self.db_service.get_all_providers_with_health()

    def update_provider_health_status(
        self, provider_name: str, health_status: str
    ) -> bool:
        """Update provider health status"""
        return self.db_service.update_provider_health_status(
            provider_name, health_status
        )

    def get_provider_performance_stats(self, provider_name: str) -> Dict[str, Any]:
        """Get provider performance statistics"""
        return self.db_service.get_provider_performance_stats(provider_name)

    def get_provider_recommendations(
        self, model_name: str = None
    ) -> List[Dict[str, Any]]:
        """Get provider recommendations"""
        return self.db_service.get_provider_recommendations(model_name)

    def get_best_provider_for_model(self, model_name: str) -> Optional[LLMProvider]:
        """Get best provider for specified model"""
        return self.db_service.get_best_provider_for_model(model_name)
