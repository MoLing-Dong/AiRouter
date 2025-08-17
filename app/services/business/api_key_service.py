"""
API Key Business Service
提供API密钥相关的业务逻辑
"""

from typing import Dict, Any, Optional, List
from app.services.repositories.api_key_repository import ApiKeyRepository
from app.services.repositories.provider_repository import ProviderRepository
from app.models import (
    LLMProviderApiKeyCreate,
    LLMProviderApiKeyUpdate,
    LLMProviderApiKey,
)
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ApiKeyService:
    """Business service for API key operations"""

    def __init__(
        self, api_key_repo: ApiKeyRepository, provider_repo: ProviderRepository
    ):
        self.api_key_repo = api_key_repo
        self.provider_repo = provider_repo

    def create_api_key(self, api_key_data: LLMProviderApiKeyCreate) -> Dict[str, Any]:
        """Create API key"""
        logger.info(
            f"🔄 Starting API key creation for provider {api_key_data.provider_id}"
        )
        logger.debug(f"   📋 API key data: {api_key_data.dict()}")

        # Validate provider exists and is enabled
        provider = self.provider_repo.get_by_id(api_key_data.provider_id)
        if not provider:
            raise ValueError(
                f"Provider with ID {api_key_data.provider_id} does not exist"
            )
        if not provider.is_enabled:
            raise ValueError(f"Provider with ID {api_key_data.provider_id} is disabled")

        # Check if API key with same name already exists for this provider
        existing = self.api_key_repo.get_by_name(
            api_key_data.provider_id, api_key_data.name
        )
        if existing:
            raise ValueError(
                f"API key with name '{api_key_data.name}' already exists for provider {api_key_data.provider_id}"
            )

        # Create API key
        api_key = self.api_key_repo.create_with_validation(api_key_data.dict())

        logger.info(
            f"✅ Successfully created API key '{api_key.name}' (ID: {api_key.id}) for provider {api_key_data.provider_id}"
        )
        logger.debug(
            f"   📍 API key details: name='{api_key.name}', weight={api_key.weight}, preferred={api_key.is_preferred}, enabled={api_key.is_enabled}"
        )

        return {
            "message": "API key created successfully",
            "api_key_id": api_key.id,
            "name": api_key.name,
            "provider_id": api_key.provider_id,
            "weight": api_key.weight,
            "is_preferred": api_key.is_preferred,
            "is_enabled": api_key.is_enabled,
        }

    def get_api_key(self, api_key_id: int) -> Optional[LLMProviderApiKey]:
        """Get API key by ID"""
        return self.api_key_repo.get_by_id(api_key_id)

    def get_api_keys_by_provider(
        self, provider_id: int, enabled_only: bool = True
    ) -> List[LLMProviderApiKey]:
        """Get all API keys for a provider"""
        return self.api_key_repo.get_by_provider_id(provider_id, enabled_only)

    def get_best_api_key(self, provider_id: int) -> Optional[LLMProviderApiKey]:
        """Get best API key for a provider based on weight and preference"""
        return self.api_key_repo.get_best_api_key(provider_id)

    def get_api_key_by_name(
        self, provider_id: int, name: str
    ) -> Optional[LLMProviderApiKey]:
        """Get API key by name for a specific provider"""
        return self.api_key_repo.get_by_name(provider_id, name)

    def update_api_key(
        self, api_key_id: int, update_data: LLMProviderApiKeyUpdate
    ) -> Optional[LLMProviderApiKey]:
        """Update API key"""
        return self.api_key_repo.update_with_validation(
            api_key_id, update_data.dict(exclude_unset=True)
        )

    def delete_api_key(self, api_key_id: int) -> bool:
        """Delete API key"""
        return self.api_key_repo.delete(api_key_id)

    def update_usage_count(self, api_key_id: int, increment: bool = True) -> bool:
        """Update API key usage count"""
        return self.api_key_repo.update_usage_count(api_key_id, increment)

    def enable_api_key(self, api_key_id: int) -> bool:
        """Enable API key"""
        return self.api_key_repo.update_enabled_status(api_key_id, True)

    def disable_api_key(self, api_key_id: int) -> bool:
        """Disable API key"""
        return self.api_key_repo.update_enabled_status(api_key_id, False)

    def update_preferred_status(self, api_key_id: int, is_preferred: bool) -> bool:
        """Update API key preferred status"""
        return self.api_key_repo.update_preferred_status(api_key_id, is_preferred)

    def get_api_key_statistics(
        self, provider_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get API key statistics"""
        return self.api_key_repo.get_api_key_statistics(provider_id)

    def check_quota_exceeded(self, api_key_id: int) -> bool:
        """Check if API key daily quota is exceeded"""
        return self.api_key_repo.check_quota_exceeded(api_key_id)

    def reset_daily_usage(self, provider_id: int) -> bool:
        """Reset daily usage count for all API keys of a provider"""
        return self.api_key_repo.reset_daily_usage(provider_id)

    def get_api_keys_by_endpoint(self, base_url: str) -> List[LLMProviderApiKey]:
        """Get API keys by base URL"""
        return self.api_key_repo.get_api_keys_by_endpoint(base_url)

    def rotate_api_key(self, api_key_id: int, new_api_key: str) -> bool:
        """Rotate API key (update the actual key value)"""

        def update_key_value(session):
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == api_key_id)
                .first()
            )
            if not api_key:
                return False

            api_key.api_key = new_api_key
            session.flush()
            return True

        return self.api_key_repo.tx_manager.execute_in_transaction(
            update_key_value, f"Rotate API key {api_key_id}"
        )

    def get_available_api_keys_for_provider(
        self, provider_id: int
    ) -> List[LLMProviderApiKey]:
        """Get available API keys for a provider (enabled and not quota exceeded)"""
        api_keys = self.get_api_keys_by_provider(provider_id, enabled_only=True)

        available_keys = []
        for api_key in api_keys:
            if not self.check_quota_exceeded(api_key.id):
                available_keys.append(api_key)

        return available_keys

    def get_api_key_health_status(self, api_key_id: int) -> Dict[str, Any]:
        """Get comprehensive health status of an API key"""
        api_key = self.get_api_key(api_key_id)
        if not api_key:
            return {"healthy": False, "reason": "API key not found"}

        if not api_key.is_enabled:
            return {"healthy": False, "reason": "API key is disabled"}

        # Check quota
        quota_exceeded = self.check_quota_exceeded(api_key_id)
        if quota_exceeded:
            return {"healthy": False, "reason": "Daily quota exceeded"}

        # Check provider health
        provider = self.provider_repo.get_by_id(api_key.provider_id)
        if not provider or not provider.is_enabled:
            return {
                "healthy": False,
                "reason": "Provider is disabled or does not exist",
            }

        return {
            "healthy": True,
            "api_key": api_key,
            "provider": provider,
            "usage_count": api_key.usage_count,
            "daily_quota": api_key.daily_quota,
            "quota_remaining": (
                (api_key.daily_quota - api_key.usage_count)
                if api_key.daily_quota
                else None
            ),
            "weight": api_key.weight,
            "is_preferred": api_key.is_preferred,
        }

    def bulk_update_api_keys(self, updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Bulk update multiple API keys"""
        results = {"success": [], "failed": [], "total": len(updates)}

        for update in updates:
            try:
                api_key_id = update.get("api_key_id")
                update_data = update.get("update_data", {})

                if not api_key_id:
                    results["failed"].append(
                        {"error": "Missing api_key_id", "data": update}
                    )
                    continue

                updated = self.update_api_key(api_key_id, update_data)
                if updated:
                    results["success"].append(
                        {"api_key_id": api_key_id, "status": "updated"}
                    )
                else:
                    results["failed"].append(
                        {"api_key_id": api_key_id, "error": "Update failed"}
                    )

            except Exception as e:
                results["failed"].append({"error": str(e), "data": update})

        logger.info(
            f"Bulk update completed: {len(results['success'])} successful, {len(results['failed'])} failed"
        )
        return results
