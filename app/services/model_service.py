from sqlalchemy.orm import Session
from typing import List, Dict, Optional, Any
from datetime import datetime
import time
from ..models import (
    LLMModel,
    LLMModelCreate,
    LLMModelCapability,
    Capability,
)
from .database_service import DatabaseService
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ModelService:
    """Model management service"""

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def get_all_models(self, is_enabled: Optional[bool] = None) -> List[Any]:
        """Get all models from database with optional filtering"""
        return self.db_service.get_all_models(is_enabled)

    def get_model_by_name(
        self, model_name: str, is_enabled: bool = None
    ) -> Optional[LLMModel]:
        """Get model by name"""
        return self.db_service.get_model_by_name(model_name, is_enabled)

    def create_model(self, model_data: LLMModelCreate) -> LLMModel:
        """Create model"""
        return self.db_service.create_model(model_data)

    def update_model_enabled_status(self, model_name: str, enabled: bool) -> bool:
        """Update model enabled status"""
        return self.db_service.update_model_enabled_status(model_name, enabled)

    def get_model_config_from_db(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model configuration from database"""
        return self.db_service.get_model_config_from_db(model_name)

    def get_model_config_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get single model configuration by name"""
        return self.db_service.get_model_config_by_name(model_name)

    def get_model_updated_timestamp(self, model_name: str) -> Optional[float]:
        """Get model updated timestamp for version checking"""
        return self.db_service.get_model_updated_timestamp(model_name)

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """Get all model configurations from database"""
        return self.db_service.get_all_model_configs_from_db()

    def get_model_capabilities(self, model_id: int) -> List[Dict[str, Any]]:
        """Get model capabilities by model ID"""
        return self.db_service.get_model_capabilities(model_id)

    def add_model_capability(self, model_id: int, capability_name: str) -> bool:
        """Add capability to model"""
        return self.db_service.add_model_capability(model_id, capability_name)

    def remove_model_capability(self, model_id: int, capability_name: str) -> bool:
        """Remove capability from model"""
        return self.db_service.remove_model_capability(model_id, capability_name)

    def get_all_capabilities(self) -> List[Dict[str, Any]]:
        """Get all available capabilities"""
        return self.db_service.get_all_capabilities()

    def get_all_models_capabilities_batch(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get capabilities for multiple models in batch"""
        return self.db_service.get_all_models_capabilities_batch(model_ids)
