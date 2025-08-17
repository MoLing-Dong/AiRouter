"""
API Key Repository
提供API密钥相关的数据访问操作
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.services.base.repository_base import BaseRepository
from app.models import (
    LLMProviderApiKey,
    LLMProviderApiKeyCreate,
    LLMProviderApiKeyUpdate,
)


class ApiKeyRepository(BaseRepository[LLMProviderApiKey]):
    """Repository for API key operations"""

    def __init__(self, transaction_manager):
        super().__init__(transaction_manager, LLMProviderApiKey)

    def validate_entity(self, entity_data: Dict[str, Any]) -> None:
        """Validate API key data"""
        required_fields = ["provider_id", "api_key"]
        for field in required_fields:
            if field not in entity_data or not entity_data[field]:
                raise ValueError(f"Field '{field}' is required for API key creation")

        # Validate weight range
        if "weight" in entity_data:
            weight = entity_data["weight"]
            if not isinstance(weight, int) or weight < 1 or weight > 100:
                raise ValueError("Weight must be an integer between 1 and 100")

        # Validate daily quota
        if "daily_quota" in entity_data and entity_data["daily_quota"]:
            quota = entity_data["daily_quota"]
            if not isinstance(quota, int) or quota < 0:
                raise ValueError("Daily quota must be a non-negative integer")

    def get_by_provider_id(
        self, provider_id: int, enabled_only: bool = True
    ) -> List[LLMProviderApiKey]:
        """Get all API keys for a provider"""
        filters = {"provider_id": provider_id}
        if enabled_only:
            filters["is_enabled"] = True

        return self.get_all(filters=filters, order_by="weight")

    def get_best_api_key(self, provider_id: int) -> Optional[LLMProviderApiKey]:
        """Get best API key for a provider based on weight and preference"""

        def operation(session: Session) -> Optional[LLMProviderApiKey]:
            return (
                session.query(LLMProviderApiKey)
                .filter(
                    LLMProviderApiKey.provider_id == provider_id,
                    LLMProviderApiKey.is_enabled == True,
                )
                .order_by(
                    LLMProviderApiKey.is_preferred.desc(),
                    LLMProviderApiKey.weight.desc(),
                )
                .first()
            )

        return self.tx_manager.execute_in_transaction(
            operation, f"Get best API key for provider {provider_id}"
        )

    def get_by_name(self, provider_id: int, name: str) -> Optional[LLMProviderApiKey]:
        """Get API key by name for a specific provider"""

        def operation(session: Session) -> Optional[LLMProviderApiKey]:
            return (
                session.query(LLMProviderApiKey)
                .filter(
                    LLMProviderApiKey.provider_id == provider_id,
                    LLMProviderApiKey.name == name,
                )
                .first()
            )

        return self.tx_manager.execute_in_transaction(
            operation, f"Get API key by name '{name}' for provider {provider_id}"
        )

    def update_usage_count(self, api_key_id: int, increment: bool = True) -> bool:
        """Update API key usage count"""

        def operation(session: Session) -> bool:
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == api_key_id)
                .first()
            )
            if not api_key:
                return False

            if increment:
                api_key.usage_count += 1
            else:
                api_key.usage_count = max(0, api_key.usage_count - 1)

            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Update API key {api_key_id} usage count"
        )

    def update_enabled_status(self, api_key_id: int, enabled: bool) -> bool:
        """Update API key enabled status"""

        def operation(session: Session) -> bool:
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == api_key_id)
                .first()
            )
            if not api_key:
                return False

            api_key.is_enabled = enabled
            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Update API key {api_key_id} enabled status to {enabled}"
        )

    def update_preferred_status(self, api_key_id: int, is_preferred: bool) -> bool:
        """Update API key preferred status"""

        def operation(session: Session) -> bool:
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == api_key_id)
                .first()
            )
            if not api_key:
                return False

            api_key.is_preferred = is_preferred
            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Update API key {api_key_id} preferred status to {is_preferred}"
        )

    def get_api_key_statistics(
        self, provider_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get API key statistics"""

        def operation(session: Session) -> Dict[str, Any]:
            query = session.query(LLMProviderApiKey)

            if provider_id:
                query = query.filter(LLMProviderApiKey.provider_id == provider_id)

            total_keys = query.count()
            enabled_keys = query.filter(LLMProviderApiKey.is_enabled == True).count()
            preferred_keys = query.filter(
                LLMProviderApiKey.is_preferred == True
            ).count()

            # Count by weight ranges
            weight_ranges = {
                "low": query.filter(LLMProviderApiKey.weight.between(1, 25)).count(),
                "medium": query.filter(
                    LLMProviderApiKey.weight.between(26, 75)
                ).count(),
                "high": query.filter(LLMProviderApiKey.weight.between(76, 100)).count(),
            }

            return {
                "total_keys": total_keys,
                "enabled_keys": enabled_keys,
                "disabled_keys": total_keys - enabled_keys,
                "preferred_keys": preferred_keys,
                "by_weight": weight_ranges,
            }

        description = (
            f"Get API key statistics for provider {provider_id}"
            if provider_id
            else "Get API key statistics"
        )
        return self.tx_manager.execute_in_transaction(operation, description)

    def check_quota_exceeded(self, api_key_id: int) -> bool:
        """Check if API key daily quota is exceeded"""

        def operation(session: Session) -> bool:
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == api_key_id)
                .first()
            )
            if not api_key:
                return True  # Consider as exceeded if not found

            if not api_key.daily_quota:
                return False  # No quota limit

            return api_key.usage_count >= api_key.daily_quota

        return self.tx_manager.execute_in_transaction(
            operation, f"Check quota exceeded for API key {api_key_id}"
        )

    def reset_daily_usage(self, provider_id: int) -> bool:
        """Reset daily usage count for all API keys of a provider"""

        def operation(session: Session) -> bool:
            api_keys = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.provider_id == provider_id)
                .all()
            )

            for api_key in api_keys:
                api_key.usage_count = 0

            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Reset daily usage for provider {provider_id}"
        )

    def get_api_keys_by_endpoint(self, base_url: str) -> List[LLMProviderApiKey]:
        """Get API keys by base URL"""

        def operation(session: Session) -> List[LLMProviderApiKey]:
            return (
                session.query(LLMProviderApiKey)
                .filter(
                    LLMProviderApiKey.base_url == base_url,
                    LLMProviderApiKey.is_enabled == True,
                )
                .all()
            )

        return self.tx_manager.execute_in_transaction(
            operation, f"Get API keys by endpoint {base_url}"
        )
