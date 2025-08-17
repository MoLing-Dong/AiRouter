"""
Model-Provider Repository
提供模型供应商关联相关的数据访问操作
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.services.base.repository_base import BaseRepository
from app.models import LLMModelProvider, LLMModelProviderCreate, LLMModelProviderUpdate


class ModelProviderRepository(BaseRepository[LLMModelProvider]):
    """Repository for model-provider association operations"""

    def __init__(self, transaction_manager):
        super().__init__(transaction_manager, LLMModelProvider)

    def validate_entity(self, entity_data: Dict[str, Any]) -> None:
        """Validate model-provider association data"""
        required_fields = ["llm_id", "provider_id"]
        for field in required_fields:
            if field not in entity_data:
                raise ValueError(
                    f"Field '{field}' is required for model-provider association"
                )

        # Validate weight range
        if "weight" in entity_data:
            weight = entity_data["weight"]
            if not isinstance(weight, int) or weight < 1 or weight > 100:
                raise ValueError("Weight must be an integer between 1 and 100")

    def get_by_model_and_provider(
        self, model_id: int, provider_id: int
    ) -> Optional[LLMModelProvider]:
        """Get association by model ID and provider ID"""

        def operation(session: Session) -> Optional[LLMModelProvider]:
            return (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

        return self.tx_manager.execute_in_transaction(
            operation,
            f"Get model-provider association: model {model_id}, provider {provider_id}",
        )

    def get_by_model_id(
        self, model_id: int, enabled_only: bool = True
    ) -> List[LLMModelProvider]:
        """Get all providers for a model"""
        filters = {"llm_id": model_id}
        if enabled_only:
            filters["is_enabled"] = True

        return self.get_all(filters=filters, order_by="weight")

    def get_by_provider_id(
        self, provider_id: int, enabled_only: bool = True
    ) -> List[LLMModelProvider]:
        """Get all models for a provider"""
        filters = {"provider_id": provider_id}
        if enabled_only:
            filters["is_enabled"] = True

        return self.get_all(filters=filters, order_by="weight")

    def get_enabled_associations(self) -> List[LLMModelProvider]:
        """Get all enabled associations"""
        return self.get_all(filters={"is_enabled": True})

    def update_weight(self, association_id: int, new_weight: int) -> bool:
        """Update association weight"""

        def operation(session: Session) -> bool:
            association = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.id == association_id)
                .first()
            )
            if not association:
                return False

            if new_weight < 1 or new_weight > 100:
                raise ValueError("Weight must be between 1 and 100")

            association.weight = new_weight
            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Update association {association_id} weight to {new_weight}"
        )

    def update_preferred_status(self, association_id: int, is_preferred: bool) -> bool:
        """Update association preferred status"""

        def operation(session: Session) -> bool:
            association = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.id == association_id)
                .first()
            )
            if not association:
                return False

            association.is_preferred = is_preferred
            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation,
            f"Update association {association_id} preferred status to {is_preferred}",
        )

    def get_best_provider_for_model(self, model_id: int) -> Optional[LLMModelProvider]:
        """Get best provider for a model based on weight and preference"""

        def operation(session: Session) -> Optional[LLMModelProvider]:
            return (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.is_enabled == True,
                )
                .order_by(
                    LLMModelProvider.is_preferred.desc(), LLMModelProvider.weight.desc()
                )
                .first()
            )

        return self.tx_manager.execute_in_transaction(
            operation, f"Get best provider for model {model_id}"
        )

    def get_model_provider_details(
        self, model_id: int, provider_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get detailed association information with model and provider data"""

        def operation(session: Session) -> Optional[Dict[str, Any]]:
            from app.models import LLMModel, LLMProvider

            association = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

            if not association:
                return None

            model = session.query(LLMModel).filter(LLMModel.id == model_id).first()
            provider = (
                session.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
            )

            return {"association": association, "model": model, "provider": provider}

        return self.tx_manager.execute_in_transaction(
            operation,
            f"Get detailed association: model {model_id}, provider {provider_id}",
        )

    def get_association_statistics(self) -> Dict[str, Any]:
        """Get association statistics"""

        def operation(session: Session) -> Dict[str, Any]:
            total_associations = session.query(LLMModelProvider).count()
            enabled_associations = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.is_enabled == True)
                .count()
            )
            preferred_associations = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.is_preferred == True)
                .count()
            )

            # Count by weight ranges
            weight_ranges = {
                "low": session.query(LLMModelProvider)
                .filter(LLMModelProvider.weight.between(1, 25))
                .count(),
                "medium": session.query(LLMModelProvider)
                .filter(LLMModelProvider.weight.between(26, 75))
                .count(),
                "high": session.query(LLMModelProvider)
                .filter(LLMModelProvider.weight.between(76, 100))
                .count(),
            }

            return {
                "total_associations": total_associations,
                "enabled_associations": enabled_associations,
                "disabled_associations": total_associations - enabled_associations,
                "preferred_associations": preferred_associations,
                "by_weight": weight_ranges,
            }

        return self.tx_manager.execute_in_transaction(
            operation, "Get association statistics"
        )

    def bulk_update_weights(self, updates: List[Dict[str, Any]]) -> bool:
        """Bulk update association weights"""

        def operation(session: Session) -> bool:
            for update in updates:
                association_id = update.get("association_id")
                new_weight = update.get("weight")

                if not association_id or not new_weight:
                    continue

                if new_weight < 1 or new_weight > 100:
                    raise ValueError(f"Weight {new_weight} must be between 1 and 100")

                association = (
                    session.query(LLMModelProvider)
                    .filter(LLMModelProvider.id == association_id)
                    .first()
                )
                if association:
                    association.weight = new_weight

            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Bulk update {len(updates)} association weights"
        )
