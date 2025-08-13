from typing import Optional
from app.services.adapter_manager import ModelAdapterManager
from app.core.adapters.base import BaseAdapter, ChatRequest, ChatResponse
from config.settings import ModelConfig
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()

# Global adapter manager instance - provide unified service interface
adapter_manager = ModelAdapterManager()


def get_adapter(model_name: str) -> Optional[BaseAdapter]:
    """Get the best adapter for the model (compatibility function)"""
    return adapter_manager.get_best_adapter(model_name)


def register_model(model_name: str, model_config: ModelConfig):
    """Register model configuration (compatibility function)"""
    adapter_manager.register_model(model_name, model_config)


async def chat_completion(model_name: str, request: ChatRequest) -> ChatResponse:
    """Execute chat completion (compatibility function)"""
    adapter = get_adapter(model_name)
    if not adapter:
        raise ValueError(f"No available adapter: {model_name}")
    return await adapter.chat_completion(request)


def get_available_models() -> list:
    """Get all available models (compatibility function)"""
    return adapter_manager.get_available_models()


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get model configuration (compatibility function)"""
    return adapter_manager.get_model_config(model_name)


async def health_check_model(model_name: str) -> dict:
    """Check model health status (compatibility function)"""
    return await adapter_manager.health_check_model(model_name)


async def health_check_all() -> dict:
    """Check all model health status (compatibility function)"""
    return await adapter_manager.health_check_all()


def refresh_from_database():
    """Refresh model configuration from database (compatibility function)"""
    adapter_manager.refresh_from_database()


def set_use_database(use_db: bool):
    """Set whether to use database configuration (compatibility function)"""
    adapter_manager.set_use_database(use_db)
