"""
Model Business Service
提供模型相关的业务逻辑
"""

from typing import Dict, Any, Optional, List
from app.services.repositories.model_repository import ModelRepository
from app.services.repositories.model_provider_repository import ModelProviderRepository
from app.services.repositories.provider_repository import ProviderRepository
from app.models import LLMModelCreate, LLMModelUpdate, LLMModel
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ModelService:
    """Business service for model operations"""

    def __init__(
        self,
        model_repo: ModelRepository,
        provider_repo: ProviderRepository,
        model_provider_repo: ModelProviderRepository,
    ):
        self.model_repo = model_repo
        self.provider_repo = provider_repo
        self.model_provider_repo = model_provider_repo

    def create_model(self, model_data: LLMModelCreate) -> Dict[str, Any]:
        """Create model with optional provider association"""
        logger.info(f"🔄 Starting model creation process for '{model_data.name}'")
        logger.debug(f"   📋 Model data: {model_data.dict()}")

        # Extract provider association data
        provider_id = getattr(model_data, "provider_id", None)
        provider_weight = getattr(model_data, "provider_weight", 10)
        is_provider_preferred = getattr(model_data, "is_provider_preferred", False)

        # Prepare model data (excluding provider fields)
        model_dict = model_data.dict()
        model_dict.pop("provider_id", None)
        model_dict.pop("provider_weight", None)
        model_dict.pop("is_provider_preferred", None)

        # Create model
        model = self.model_repo.create_with_validation(model_dict)

        # Create provider association if specified
        provider_info = None
        if provider_id:
            try:
                # Validate provider exists and is enabled
                provider = self.provider_repo.get_by_id(provider_id)
                if not provider:
                    raise ValueError(f"Provider with ID {provider_id} does not exist")
                if not provider.is_enabled:
                    raise ValueError(f"Provider with ID {provider_id} is disabled")

                # Check if association already exists
                existing_association = (
                    self.model_provider_repo.get_by_model_and_provider(
                        model.id, provider_id
                    )
                )
                if existing_association:
                    raise ValueError(
                        f"Model-provider association already exists for model {model.id} and provider {provider_id}"
                    )

                # Create model-provider association
                association_data = {
                    "llm_id": model.id,
                    "provider_id": provider_id,
                    "weight": provider_weight,
                    "is_preferred": is_provider_preferred,
                    "is_enabled": True,
                }

                association = self.model_provider_repo.create_with_validation(
                    association_data
                )
                logger.info(
                    f"✅ Created model-provider association: model {model.id} -> provider {provider_id}"
                )

                provider_info = {
                    "provider_id": provider_id,
                    "provider_name": provider.name,
                    "weight": provider_weight,
                    "is_preferred": is_provider_preferred,
                }

            except Exception as e:
                logger.error(f"❌ Failed to create provider association: {e}")
                # Continue without provider association
                provider_info = None

        # Prepare response
        response = {
            "message": "Model created successfully",
            "id": model.id,
            "name": model.name,
            "llm_type": model.llm_type,
            "is_enabled": model.is_enabled,
        }

        if provider_info:
            response["provider_info"] = provider_info

        # Log success details
        if provider_info:
            logger.info(
                f"✅ Successfully created model '{model.name}' (ID: {model.id}) with provider association (ID: {provider_id})"
            )
            logger.debug(
                f"   📍 Model details: name='{model.name}', type='{model.llm_type}', enabled={model.is_enabled}"
            )
            logger.debug(
                f"   🔗 Provider association: provider_id={provider_id}, weight={provider_weight}, preferred={is_provider_preferred}"
            )
        else:
            logger.info(
                f"✅ Successfully created model '{model.name}' (ID: {model.id}) without provider association"
            )
            logger.debug(
                f"   📍 Model details: name='{model.name}', type='{model.llm_type}', enabled={model.is_enabled}"
            )

        return response

    def get_model(self, model_id: int) -> Optional[LLMModel]:
        """Get model by ID"""
        return self.model_repo.get_by_id(model_id)

    def get_model_by_name(self, name: str) -> Optional[LLMModel]:
        """Get model by name"""
        return self.model_repo.get_by_name(name)

    def get_all_models(self, enabled_only: bool = True) -> List[LLMModel]:
        """Get all models"""
        if enabled_only:
            return self.model_repo.get_enabled_models()
        return self.model_repo.get_all()

    def get_models_by_type(self, model_type: str) -> List[LLMModel]:
        """Get models by type"""
        return self.model_repo.get_models_by_type(model_type)

    def update_model(
        self, model_id: int, update_data: LLMModelUpdate
    ) -> Optional[LLMModel]:
        """Update model"""
        return self.model_repo.update_with_validation(
            model_id, update_data.dict(exclude_unset=True)
        )

    def delete_model(self, model_id: int) -> bool:
        """Delete model"""
        # Check if model has provider associations
        associations = self.model_provider_repo.get_by_model_id(
            model_id, enabled_only=False
        )
        if associations:
            logger.warning(
                f"⚠️ Model {model_id} has {len(associations)} provider associations. Deleting them first."
            )
            for association in associations:
                self.model_provider_repo.delete(association.id)

        return self.model_repo.delete(model_id)

    def enable_model(self, model_id: int) -> bool:
        """Enable model"""
        return self.model_repo.update_enabled_status(model_id, True)

    def disable_model(self, model_id: int) -> bool:
        """Disable model"""
        return self.model_repo.update_enabled_status(model_id, False)

    def get_model_with_providers(self, model_id: int) -> Optional[Dict[str, Any]]:
        """Get model with its provider associations"""
        return self.model_repo.get_model_with_providers(model_id)

    def search_models(
        self, search_term: str, model_type: Optional[str] = None
    ) -> List[LLMModel]:
        """Search models"""
        return self.model_repo.search_models(search_term, model_type)

    def get_model_statistics(self) -> Dict[str, Any]:
        """Get model statistics"""
        return self.model_repo.get_model_statistics()

    def create_model_with_provider(
        self,
        model_data: LLMModelCreate,
        provider_id: int,
        weight: int = 10,
        is_preferred: bool = False,
    ) -> Dict[str, Any]:
        """Create model and associate with provider in one transaction"""
        # Set provider fields
        model_data.provider_id = provider_id
        model_data.provider_weight = weight
        model_data.is_provider_preferred = is_preferred

        return self.create_model(model_data)

    def get_models_by_provider(self, provider_id: int) -> List[LLMModel]:
        """Get all models associated with a provider"""
        associations = self.model_provider_repo.get_by_provider_id(provider_id)
        model_ids = [assoc.llm_id for assoc in associations]

        if not model_ids:
            return []

        # Get models in one query
        def get_models_by_ids(session):
            from app.models import LLMModel

            return session.query(LLMModel).filter(LLMModel.id.in_(model_ids)).all()

        return self.model_repo.tx_manager.execute_in_transaction(
            get_models_by_ids, f"Get models for provider {provider_id}"
        )
