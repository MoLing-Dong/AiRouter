# Export database service
from .database_service import db_service

# Export adapter related services
from .adapter_manager import ModelAdapterManager
from .adapter_factory import AdapterFactory
from .adapter_database_service import ModelDatabaseService
from .adapter_health_checker import HealthChecker
from .adapter_compatibility import (
    adapter_manager,
    get_adapter,
    register_model,
    chat_completion,
    get_available_models,
    get_model_config,
    health_check_model,
    health_check_all,
    refresh_from_database,
    set_use_database,
)

# Export router service
from .router import SmartRouter

__all__ = [
    # Database service
    "db_service",
    # Adapter service
    "ModelAdapterManager",
    "AdapterFactory",
    "ModelDatabaseService",
    "HealthChecker",
    "adapter_manager",
    "get_adapter",
    "register_model",
    "chat_completion",
    "get_available_models",
    "get_model_config",
    "health_check_model",
    "health_check_all",
    "refresh_from_database",
    "set_use_database",
    # Router service
    "SmartRouter",
]
