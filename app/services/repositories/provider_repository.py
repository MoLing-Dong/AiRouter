"""
Provider Repository
提供供应商相关的数据访问操作
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.services.base.repository_base import BaseRepository
from app.models import LLMProvider, LLMProviderCreate, LLMProviderUpdate


class ProviderRepository(BaseRepository[LLMProvider]):
    """Repository for LLM provider operations"""

    def __init__(self, transaction_manager):
        super().__init__(transaction_manager, LLMProvider)

    def validate_entity(self, entity_data: Dict[str, Any]) -> None:
        """Validate provider data"""
        required_fields = ["name", "provider_type"]
        for field in required_fields:
            if field not in entity_data or not entity_data[field]:
                raise ValueError(f"Field '{field}' is required for provider creation")

        # Check name length
        if len(entity_data["name"]) > 100:
            raise ValueError("Provider name cannot exceed 100 characters")

        # Check type validity
        valid_types = ["openai", "anthropic", "volcengine", "custom", "other"]
        if entity_data["provider_type"] not in valid_types:
            raise ValueError(f"Invalid provider type. Must be one of: {valid_types}")

    def get_by_name(self, name: str) -> Optional[LLMProvider]:
        """Get provider by name"""

        def operation(session: Session) -> Optional[LLMProvider]:
            return session.query(LLMProvider).filter(LLMProvider.name == name).first()

        return self.tx_manager.execute_in_transaction(
            operation, f"Get provider by name '{name}'"
        )

    def get_by_name_and_type(
        self, name: str, provider_type: str
    ) -> Optional[LLMProvider]:
        """Get provider by name and type"""

        def operation(session: Session) -> Optional[LLMProvider]:
            return (
                session.query(LLMProvider)
                .filter(
                    LLMProvider.name == name, LLMProvider.provider_type == provider_type
                )
                .first()
            )

        return self.tx_manager.execute_in_transaction(
            operation, f"Get provider by name '{name}' and type '{provider_type}'"
        )

    def get_enabled_providers(self) -> List[LLMProvider]:
        """Get all enabled providers"""
        return self.get_all(filters={"is_enabled": True}, order_by="name")

    def get_providers_by_type(self, provider_type: str) -> List[LLMProvider]:
        """Get providers by type"""
        return self.get_all(
            filters={"provider_type": provider_type, "is_enabled": True}
        )

    def update_enabled_status(self, provider_id: int, enabled: bool) -> bool:
        """Update provider enabled status"""

        def operation(session: Session) -> bool:
            provider = (
                session.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
            )
            if not provider:
                return False

            provider.is_enabled = enabled
            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Update provider {provider_id} enabled status to {enabled}"
        )

    def get_provider_with_models(self, provider_id: int) -> Optional[Dict[str, Any]]:
        """Get provider with its model associations"""

        def operation(session: Session) -> Optional[Dict[str, Any]]:
            provider = (
                session.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
            )
            if not provider:
                return None

            # Get model associations
            from app.models import LLMModelProvider, LLMModel

            models = (
                session.query(LLMModelProvider, LLMModel)
                .join(LLMModel, LLMModelProvider.llm_id == LLMModel.id)
                .filter(LLMModelProvider.provider_id == provider_id)
                .all()
            )

            return {
                "provider": provider,
                "models": [{"association": mp, "model": m} for mp, m in models],
            }

        return self.tx_manager.execute_in_transaction(
            operation, f"Get provider {provider_id} with models"
        )

    def search_providers(
        self, search_term: str, provider_type: Optional[str] = None
    ) -> List[LLMProvider]:
        """Search providers by name or description"""

        def operation(session: Session) -> List[LLMProvider]:
            query = session.query(LLMProvider).filter(LLMProvider.is_enabled == True)

            if provider_type:
                query = query.filter(LLMProvider.provider_type == provider_type)

            # Search in name and description
            search_filter = LLMProvider.name.ilike(
                f"%{search_term}%"
            ) | LLMProvider.description.ilike(f"%{search_term}%")
            query = query.filter(search_filter)

            return query.order_by(LLMProvider.name).all()

        return self.tx_manager.execute_in_transaction(
            operation,
            f"Search providers with term '{search_term}' and type '{provider_type}'",
        )

    def get_provider_statistics(self) -> Dict[str, Any]:
        """Get provider statistics"""

        def operation(session: Session) -> Dict[str, Any]:
            total_providers = session.query(LLMProvider).count()
            enabled_providers = (
                session.query(LLMProvider)
                .filter(LLMProvider.is_enabled == True)
                .count()
            )

            # Count by type
            type_counts = {}
            for provider_type in [
                "openai",
                "anthropic",
                "volcengine",
                "custom",
                "other",
            ]:
                count = (
                    session.query(LLMProvider)
                    .filter(
                        LLMProvider.provider_type == provider_type,
                        LLMProvider.is_enabled == True,
                    )
                    .count()
                )
                type_counts[provider_type] = count

            return {
                "total_providers": total_providers,
                "enabled_providers": enabled_providers,
                "disabled_providers": total_providers - enabled_providers,
                "by_type": type_counts,
            }

        return self.tx_manager.execute_in_transaction(
            operation, "Get provider statistics"
        )

    def get_provider_endpoints(self, provider_id: int) -> Dict[str, str]:
        """Get provider endpoints"""

        def operation(session: Session) -> Dict[str, str]:
            provider = (
                session.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
            )
            if not provider:
                return {}

            endpoints = {}
            if provider.official_endpoint:
                endpoints["official"] = provider.official_endpoint
            if provider.third_party_endpoint:
                endpoints["third_party"] = provider.third_party_endpoint

            return endpoints

        return self.tx_manager.execute_in_transaction(
            operation, f"Get provider {provider_id} endpoints"
        )
