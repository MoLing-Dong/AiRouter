"""
Services package
提供业务逻辑和数据访问服务
"""

# Base services
from .base.transaction_manager import BaseTransactionManager, DatabaseTransactionManager
from .base.repository_base import BaseRepository

# Repository implementations
from .repositories.model_repository import ModelRepository
from .repositories.provider_repository import ProviderRepository
from .repositories.model_provider_repository import ModelProviderRepository
from .repositories.api_key_repository import ApiKeyRepository

# Business services
from .business.model_service import ModelService
from .business.provider_service import ProviderService
from .business.model_provider_service import ModelProviderService
from .business.api_key_service import ApiKeyService

# Service factory
from .service_factory import ServiceFactory

# Legacy services (for backward compatibility)
from .database_service import db_service
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
from .router import SmartRouter

__all__ = [
    # Base services
    "BaseTransactionManager",
    "DatabaseTransactionManager",
    "BaseRepository",
    # Repository implementations
    "ModelRepository",
    "ProviderRepository",
    "ModelProviderRepository",
    "ApiKeyRepository",
    # Business services
    "ModelService",
    "ProviderService",
    "ModelProviderService",
    "ApiKeyService",
    # Service factory
    "ServiceFactory",
    # Legacy services (for backward compatibility)
    "db_service",
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
    "SmartRouter",
]
