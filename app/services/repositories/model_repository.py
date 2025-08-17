"""
Model Repository
提供模型相关的数据访问操作
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from app.services.base.repository_base import BaseRepository
from app.models import LLMModel, LLMModelCreate, LLMModelUpdate


class ModelRepository(BaseRepository[LLMModel]):
    """Repository for LLM model operations"""

    def __init__(self, transaction_manager):
        super().__init__(transaction_manager, LLMModel)

    def validate_entity(self, entity_data: Dict[str, Any]) -> None:
        """Validate model data"""
        required_fields = ["name", "llm_type"]
        for field in required_fields:
            if field not in entity_data or not entity_data[field]:
                raise ValueError(f"Field '{field}' is required for model creation")

        # Check name length
        if len(entity_data["name"]) > 100:
            raise ValueError("Model name cannot exceed 100 characters")

        # Check type validity
        valid_types = ["chat", "completion", "embedding", "PRIVATE"]
        if entity_data["llm_type"] not in valid_types:
            raise ValueError(f"Invalid model type. Must be one of: {valid_types}")

    def get_by_name(self, name: str) -> Optional[LLMModel]:
        """Get model by name"""

        def operation(session: Session) -> Optional[LLMModel]:
            return session.query(LLMModel).filter(LLMModel.name == name).first()

        return self.tx_manager.execute_in_transaction(
            operation, f"Get model by name '{name}'"
        )

    def get_enabled_models(self) -> List[LLMModel]:
        """Get all enabled models"""
        return self.get_all(filters={"is_enabled": True}, order_by="name")

    def get_models_by_type(self, model_type: str) -> List[LLMModel]:
        """Get models by type"""
        return self.get_all(filters={"llm_type": model_type, "is_enabled": True})

    def update_enabled_status(self, model_id: int, enabled: bool) -> bool:
        """Update model enabled status"""

        def operation(session: Session) -> bool:
            model = session.query(LLMModel).filter(LLMModel.id == model_id).first()
            if not model:
                return False

            model.is_enabled = enabled
            session.flush()
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Update model {model_id} enabled status to {enabled}"
        )

    def get_model_with_providers(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get model with its provider associations"""

        def operation(session: Session) -> Optional[Dict[str, Any]]:
            model = session.query(LLMModel).filter(LLMModel.id == model_id).first()
            if not model:
                return None

            # Get provider associations
            from app.models import LLMModelProvider, LLMProvider

            providers = (
                session.query(LLMModelProvider, LLMProvider)
                .join(LLMProvider, LLMModelProvider.provider_id == LLMProvider.id)
                .filter(LLMModelProvider.llm_id == model_id)
                .all()
            )

            return {
                "model": model,
                "providers": [
                    {"association": mp, "provider": p} for mp, p in providers
                ],
            }

        return self.tx_manager.execute_in_transaction(
            operation, f"Get model {model_id} with providers"
        )

    def search_models(
        self, search_term: str, model_type: Optional[str] = None
    ) -> List[LLMModel]:
        """Search models by name or description"""

        def operation(session: Session) -> List[LLMModel]:
            query = session.query(LLMModel).filter(LLMModel.is_enabled == True)

            if model_type:
                query = query.filter(LLMModel.llm_type == model_type)

            # Search in name and description
            search_filter = LLMModel.name.ilike(
                f"%{search_term}%"
            ) | LLMModel.description.ilike(f"%{search_term}%")
            query = query.filter(search_filter)

            return query.order_by(LLMModel.name).all()

        return self.tx_manager.execute_in_transaction(
            operation,
            f"Search models with term '{search_term}' and type '{model_type}'",
        )

    def get_model_statistics(self) -> Dict[str, Any]:
        """Get model statistics"""

        def operation(session: Session) -> Dict[str, Any]:
            total_models = session.query(LLMModel).count()
            enabled_models = (
                session.query(LLMModel).filter(LLMModel.is_enabled == True).count()
            )

            # Count by type
            type_counts = {}
            for model_type in ["chat", "completion", "embedding", "PRIVATE"]:
                count = (
                    session.query(LLMModel)
                    .filter(
                        LLMModel.llm_type == model_type, LLMModel.is_enabled == True
                    )
                    .count()
                )
                type_counts[model_type] = count

            return {
                "total_models": total_models,
                "enabled_models": enabled_models,
                "disabled_models": total_models - enabled_models,
                "by_type": type_counts,
            }

        return self.tx_manager.execute_in_transaction(operation, "Get model statistics")
