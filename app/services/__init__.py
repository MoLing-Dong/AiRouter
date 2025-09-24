"""
AI Router Services Module
AI路由器服务模块 - 重新组织后的清晰架构

服务分类：
- database: 数据库相关服务
- adapters: 适配器管理服务  
- load_balancing: 负载均衡和路由服务
- monitoring: 监控和性能分析服务
- core: 核心业务服务
"""

# 核心服务导入
from .model_service import ModelService
from .model_provider_service import ModelProviderService
from .provider_service import ProviderService
from .service_factory import ServiceFactory
from .service_manager import ServiceManager

# 数据库服务导入
from .database.database_service import db_service
from .database.async_database_service import async_db_service
from .database.database_service_integration import integrated_db_service

# 适配器服务导入
from .adapters.adapter_manager import adapter_manager
from .adapters.adapter_factory import AdapterFactory
from .adapters.adapter_pool import AdapterPool

# 负载均衡服务导入
from .load_balancing.load_balancing_strategies import LoadBalancingStrategy, LoadBalancingStrategyManager
from .load_balancing.router import SmartRouter

# 监控服务导入
from .monitoring.health_check_service import HealthCheckService
from .monitoring.enhanced_model_service import enhanced_model_service

__all__ = [
    # 核心服务
    "ModelService",
    "ModelProviderService", 
    "ProviderService",
    "ServiceFactory",
    "ServiceManager",
    
    # 数据库服务
    "db_service",
    "async_db_service", 
    "integrated_db_service",
    
    # 适配器服务
    "adapter_manager",
    "AdapterFactory",
    "AdapterPool",
    
    # 负载均衡服务
    "LoadBalancingStrategy",
    "Router",
    
    # 监控服务
    "HealthCheckService",
    "enhanced_model_service",
]