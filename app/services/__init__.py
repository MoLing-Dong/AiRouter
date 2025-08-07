# 导出数据库服务
from .database_service import db_service

# 导出适配器相关服务
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

# 导出路由服务
from .router import SmartRouter

__all__ = [
    # 数据库服务
    "db_service",
    # 适配器服务
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
    # 路由服务
    "SmartRouter",
]
