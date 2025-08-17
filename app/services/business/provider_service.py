"""
Provider Business Service
提供供应商相关的业务逻辑
"""

from typing import Dict, Any, Optional, List
from app.services.repositories.provider_repository import ProviderRepository
from app.services.repositories.model_provider_repository import ModelProviderRepository
from app.services.repositories.api_key_repository import ApiKeyRepository
from app.models import LLMProviderCreate, LLMProviderUpdate, LLMProvider
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ProviderService:
    """Business service for provider operations"""

    def __init__(
        self,
        provider_repo: ProviderRepository,
        model_provider_repo: ModelProviderRepository,
        api_key_repo: ApiKeyRepository,
    ):
        self.provider_repo = provider_repo
        self.model_provider_repo = model_provider_repo
        self.api_key_repo = api_key_repo

    def create_provider(self, provider_data: LLMProviderCreate) -> Dict[str, Any]:
        """Create provider"""
        logger.info(f"🔄 Starting provider creation process for '{provider_data.name}'")
        logger.debug(f"   📋 Provider data: {provider_data.dict()}")

        # Create provider
        provider = self.provider_repo.create_with_validation(provider_data.dict())

        logger.info(
            f"✅ Successfully created provider '{provider.name}' (ID: {provider.id})"
        )
        logger.debug(
            f"   📍 Provider details: name='{provider.name}', type='{provider.provider_type}', enabled={provider.is_enabled}"
        )

        return {
            "message": "Provider created successfully",
            "provider_id": provider.id,
            "provider_name": provider.name,
            "provider_type": provider.provider_type,
            "is_enabled": provider.is_enabled,
        }

    def get_provider(self, provider_id: int) -> Optional[LLMProvider]:
        """Get provider by ID"""
        return self.provider_repo.get_by_id(provider_id)

    def get_provider_by_name(self, name: str) -> Optional[LLMProvider]:
        """Get provider by name"""
        return self.provider_repo.get_by_name(name)

    def get_provider_by_name_and_type(
        self, name: str, provider_type: str
    ) -> Optional[LLMProvider]:
        """Get provider by name and type"""
        return self.provider_repo.get_by_name_and_type(name, provider_type)

    def get_all_providers(self, enabled_only: bool = True) -> List[LLMProvider]:
        """Get all providers"""
        if enabled_only:
            return self.provider_repo.get_enabled_providers()
        return self.provider_repo.get_all()

    def get_providers_by_type(self, provider_type: str) -> List[LLMProvider]:
        """Get providers by type"""
        return self.provider_repo.get_providers_by_type(provider_type)

    def update_provider(
        self, provider_id: int, update_data: LLMProviderUpdate
    ) -> Optional[LLMProvider]:
        """Update provider"""
        return self.provider_repo.update_with_validation(
            provider_id, update_data.dict(exclude_unset=True)
        )

    def delete_provider(self, provider_id: int) -> bool:
        """Delete provider"""
        # Check if provider has model associations
        associations = self.model_provider_repo.get_by_provider_id(
            provider_id, enabled_only=False
        )
        if associations:
            logger.warning(
                f"⚠️ Provider {provider_id} has {len(associations)} model associations. Deleting them first."
            )
            for association in associations:
                self.model_provider_repo.delete(association.id)

        # Check if provider has API keys
        api_keys = self.api_key_repo.get_by_provider_id(provider_id, enabled_only=False)
        if api_keys:
            logger.warning(
                f"⚠️ Provider {provider_id} has {len(api_keys)} API keys. Deleting them first."
            )
            for api_key in api_keys:
                self.api_key_repo.delete(api_key.id)

        return self.provider_repo.delete(provider_id)

    def enable_provider(self, provider_id: int) -> bool:
        """Enable provider"""
        return self.provider_repo.update_enabled_status(provider_id, True)

    def disable_provider(self, provider_id: int) -> bool:
        """Disable provider"""
        return self.provider_repo.update_enabled_status(provider_id, False)

    def get_provider_with_models(self, provider_id: int) -> Optional[Dict[str, Any]]:
        """Get provider with its model associations"""
        return self.provider_repo.get_provider_with_models(provider_id)

    def search_providers(
        self, search_term: str, provider_type: Optional[str] = None
    ) -> List[LLMProvider]:
        """Search providers"""
        return self.provider_repo.search_providers(search_term, provider_type)

    def get_provider_statistics(self) -> Dict[str, Any]:
        """Get provider statistics"""
        return self.provider_repo.get_provider_statistics()

    def get_provider_endpoints(self, provider_id: int) -> Dict[str, str]:
        """Get provider endpoints"""
        return self.provider_repo.get_provider_endpoints(provider_id)

    def get_providers_by_model(self, model_id: int) -> List[LLMProvider]:
        """Get all providers associated with a model"""
        associations = self.model_provider_repo.get_by_model_id(model_id)
        provider_ids = [assoc.provider_id for assoc in associations]

        if not provider_ids:
            return []

        # Get providers in one query
        def get_providers_by_ids(session):
            from app.models import LLMProvider

            return (
                session.query(LLMProvider)
                .filter(LLMProvider.id.in_(provider_ids))
                .all()
            )

        return self.provider_repo.tx_manager.execute_in_transaction(
            get_providers_by_ids, f"Get providers for model {model_id}"
        )

    def get_best_provider_for_model(self, model_id: int) -> Optional[LLMProvider]:
        """Get best provider for a model based on weight and preference"""
        association = self.model_provider_repo.get_best_provider_for_model(model_id)
        if not association:
            return None

        return self.provider_repo.get_by_id(association.provider_id)

    def validate_provider_availability(self, provider_id: int) -> Dict[str, Any]:
        """Validate provider availability and health"""
        provider = self.get_provider(provider_id)
        if not provider:
            return {"available": False, "reason": "Provider not found"}

        if not provider.is_enabled:
            return {"available": False, "reason": "Provider is disabled"}

        # Check if provider has any enabled API keys
        api_keys = self.api_key_repo.get_by_provider_id(provider_id, enabled_only=True)
        if not api_keys:
            return {"available": False, "reason": "No enabled API keys"}

        # Check if provider has any model associations
        associations = self.model_provider_repo.get_by_provider_id(
            provider_id, enabled_only=True
        )
        if not associations:
            return {"available": False, "reason": "No model associations"}

        return {
            "available": True,
            "provider": provider,
            "api_keys_count": len(api_keys),
            "models_count": len(associations),
        }
