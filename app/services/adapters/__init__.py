"""
适配器服务模块
管理各种AI模型适配器的生命周期和连接池
"""

from .adapter_manager import adapter_manager, ModelAdapterManager
from .adapter_factory import AdapterFactory
from .adapter_pool import AdapterPool
from .adapter_health_checker import HealthChecker

__all__ = [
    "adapter_manager",
    "ModelAdapterManager",
    "AdapterFactory", 
    "AdapterPool",
    "HealthChecker",
]