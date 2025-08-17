"""
Model-Provider Association Business Service
提供模型供应商关联相关的业务逻辑
"""

from typing import Dict, Any, Optional, List
from app.services.repositories.model_provider_repository import ModelProviderRepository
from app.services.repositories.model_repository import ModelRepository
from app.services.repositories.provider_repository import ProviderRepository
from app.models import LLMModelProviderCreate, LLMModelProviderUpdate, LLMModelProvider
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ModelProviderService:
    """Business service for model-provider association operations"""

    def __init__(
        self,
        model_provider_repo: ModelProviderRepository,
        model_repo: ModelRepository,
        provider_repo: ProviderRepository,
    ):
        self.model_provider_repo = model_provider_repo
        self.model_repo = model_repo
        self.provider_repo = provider_repo

    def create_association(
        self, association_data: LLMModelProviderCreate
    ) -> Dict[str, Any]:
        """Create model-provider association"""
        logger.info(
            f"🔄 Starting association creation: model {association_data.llm_id} -> provider {association_data.provider_id}"
        )
        logger.debug(f"   📋 Association data: {association_data.dict()}")

        # Validate model exists and is enabled
        model = self.model_repo.get_by_id(association_data.llm_id)
        if not model:
            raise ValueError(f"Model with ID {association_data.llm_id} does not exist")
        if not model.is_enabled:
            raise ValueError(f"Model with ID {association_data.llm_id} is disabled")

        # Validate provider exists and is enabled
        provider = self.provider_repo.get_by_id(association_data.provider_id)
        if not provider:
            raise ValueError(
                f"Provider with ID {association_data.provider_id} does not exist"
            )
        if not provider.is_enabled:
            raise ValueError(
                f"Provider with ID {association_data.provider_id} is disabled"
            )

        # Check if association already exists
        existing = self.model_provider_repo.get_by_model_and_provider(
            association_data.llm_id, association_data.provider_id
        )
        if existing:
            raise ValueError(
                f"Association already exists for model {association_data.llm_id} and provider {association_data.provider_id}"
            )

        # Create association
        association = self.model_provider_repo.create_with_validation(
            association_data.dict()
        )

        logger.info(
            f"✅ Successfully created association: model {association.llm_id} -> provider {association.provider_id}"
        )
        logger.debug(
            f"   📍 Association details: weight={association.weight}, preferred={association.is_preferred}, enabled={association.is_enabled}"
        )

        return {
            "message": "Association created successfully",
            "association_id": association.id,
            "model_id": association.llm_id,
            "provider_id": association.provider_id,
            "weight": association.weight,
            "is_preferred": association.is_preferred,
            "is_enabled": association.is_enabled,
        }

    def get_association(self, association_id: int) -> Optional[LLMModelProvider]:
        """Get association by ID"""
        return self.model_provider_repo.get_by_id(association_id)

    def get_association_by_model_and_provider(
        self, model_id: int, provider_id: int
    ) -> Optional[LLMModelProvider]:
        """Get association by model ID and provider ID"""
        return self.model_provider_repo.get_by_model_and_provider(model_id, provider_id)

    def get_associations_by_model(
        self, model_id: int, enabled_only: bool = True
    ) -> List[LLMModelProvider]:
        """Get all associations for a model"""
        return self.model_provider_repo.get_by_model_id(model_id, enabled_only)

    def get_associations_by_provider(
        self, provider_id: int, enabled_only: bool = True
    ) -> List[LLMModelProvider]:
        """Get all associations for a provider"""
        return self.model_provider_repo.get_by_provider_id(provider_id, enabled_only)

    def get_all_associations(self, enabled_only: bool = True) -> List[LLMModelProvider]:
        """Get all associations"""
        if enabled_only:
            return self.model_provider_repo.get_enabled_associations()
        return self.model_provider_repo.get_all()

    def update_association(
        self, association_id: int, update_data: LLMModelProviderUpdate
    ) -> Optional[LLMModelProvider]:
        """Update association"""
        return self.model_provider_repo.update_with_validation(
            association_id, update_data.dict(exclude_unset=True)
        )

    def delete_association(self, association_id: int) -> bool:
        """Delete association"""
        return self.model_provider_repo.delete(association_id)

    def update_weight(self, association_id: int, new_weight: int) -> bool:
        """Update association weight"""
        return self.model_provider_repo.update_weight(association_id, new_weight)

    def update_preferred_status(self, association_id: int, is_preferred: bool) -> bool:
        """Update association preferred status"""
        return self.model_provider_repo.update_preferred_status(
            association_id, is_preferred
        )

    def get_best_provider_for_model(self, model_id: int) -> Optional[LLMModelProvider]:
        """Get best provider for a model based on weight and preference"""
        return self.model_provider_repo.get_best_provider_for_model(model_id)

    def get_detailed_association(
        self, model_id: int, provider_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get detailed association information with model and provider data"""
        return self.model_provider_repo.get_model_provider_details(
            model_id, provider_id
        )

    def get_association_statistics(self) -> Dict[str, Any]:
        """Get association statistics"""
        return self.model_provider_repo.get_association_statistics()

    def bulk_update_weights(self, updates: List[Dict[str, Any]]) -> bool:
        """Bulk update association weights"""
        return self.model_provider_repo.bulk_update_weights(updates)

    def enable_association(self, association_id: int) -> bool:
        """Enable association"""
        return self.model_provider_repo.update_enabled_status(association_id, True)

    def disable_association(self, association_id: int) -> bool:
        """Disable association"""
        return self.model_provider_repo.update_enabled_status(association_id, False)

    def get_model_provider_matrix(self) -> Dict[str, Any]:
        """Get a matrix view of all model-provider associations"""

        def get_matrix_data(session):
            from app.models import LLMModel, LLMProvider, LLMModelProvider

            # Get all models and providers
            models = session.query(LLMModel).filter(LLMModel.is_enabled == True).all()
            providers = (
                session.query(LLMProvider).filter(LLMProvider.is_enabled == True).all()
            )

            # Get all associations
            associations = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.is_enabled == True)
                .all()
            )

            # Create association lookup
            association_lookup = {}
            for assoc in associations:
                key = (assoc.llm_id, assoc.provider_id)
                association_lookup[key] = assoc

            # Build matrix
            matrix = {
                "models": [
                    {"id": m.id, "name": m.name, "type": m.llm_type} for m in models
                ],
                "providers": [
                    {"id": p.id, "name": p.name, "type": p.provider_type}
                    for p in providers
                ],
                "associations": [],
            }

            for model in models:
                for provider in providers:
                    key = (model.id, provider.id)
                    if key in association_lookup:
                        assoc = association_lookup[key]
                        matrix["associations"].append(
                            {
                                "model_id": model.id,
                                "provider_id": provider.id,
                                "weight": assoc.weight,
                                "is_preferred": assoc.is_preferred,
                                "association_id": assoc.id,
                            }
                        )

            return matrix

        return self.model_provider_repo.tx_manager.execute_in_transaction(
            get_matrix_data, "Get model-provider association matrix"
        )

    def validate_association_health(
        self, model_id: int, provider_id: int
    ) -> Dict[str, Any]:
        """Validate the health of a specific association"""
        association = self.get_association_by_model_and_provider(model_id, provider_id)
        if not association:
            return {"healthy": False, "reason": "Association does not exist"}

        if not association.is_enabled:
            return {"healthy": False, "reason": "Association is disabled"}

        # Check model health
        model = self.model_repo.get_by_id(model_id)
        if not model or not model.is_enabled:
            return {"healthy": False, "reason": "Model is disabled or does not exist"}

        # Check provider health
        provider = self.provider_repo.get_by_id(provider_id)
        if not provider or not provider.is_enabled:
            return {
                "healthy": False,
                "reason": "Provider is disabled or does not exist",
            }

        return {
            "healthy": True,
            "association": association,
            "model": model,
            "provider": provider,
            "weight": association.weight,
            "is_preferred": association.is_preferred,
        }
