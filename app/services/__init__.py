"""
AI Router Services Module
AI路由器服务模块 - 领域驱动设计架构

架构设计：
===================
采用领域驱动设计（DDD）的垂直切分方式，按业务领域组织服务，
而不是按技术层次（如MVC的水平切分）。

业务领域（Domain）：
├── Model Domain (模型领域)
│   - 模型的全生命周期管理
│   - 模型查询和展示
│   - 模型缓存
│   - 模型与提供商关联
│
├── Capability Domain (能力领域)
│   - 能力定义和管理
│   - 模型能力关联
│
├── Provider Domain (提供商领域)
│   - 提供商管理
│   - API Key 管理
│
└── Supporting Services (支撑服务)
    - Database: 数据持久化
    - Adapters: LLM 提供商适配器
    - Load Balancing: 负载均衡和路由
    - Monitoring: 监控和健康检查
    - Infrastructure: 基础设施服务

目录结构：
===================
- model/             模型领域服务
- capability/        能力领域服务
- provider/          提供商领域服务
- database/          数据库服务
- adapters/          适配器管理
- load_balancing/    负载均衡
- monitoring/        监控服务
- infrastructure/    基础设施
"""

# ============================================================================
# Model Domain Services (模型领域服务)
# ============================================================================
from .model import (
    ModelService,
    ModelQueryService,
    model_query_service,
    ModelsCacheManager,
    models_cache,
    ModelProviderService,
)

# ============================================================================
# Capability Domain Services (能力领域服务)
# ============================================================================
from .capability import (
    CapabilityService,
    capability_service,
)

# ============================================================================
# Provider Domain Services (提供商领域服务)
# ============================================================================
from .provider import (
    ProviderService,
)

# ============================================================================
# Infrastructure Services (基础设施服务)
# ============================================================================
from .infrastructure import (
    ServiceFactory,
    ServiceManager,
)

# ============================================================================
# Database Services (数据库服务)
# ============================================================================
from .database import (
    db_service,
    async_db_service,
    sqlmodel_db_service,
)

# ============================================================================
# Adapter Services (适配器服务)
# ============================================================================
from .adapters import (
    adapter_manager,
    AdapterFactory,
    AdapterPool,
)

# ============================================================================
# Load Balancing Services (负载均衡服务)
# ============================================================================
from .load_balancing import (
    LoadBalancingStrategy,
    LoadBalancingStrategyManager,
    SmartRouter,
)

# ============================================================================
# Monitoring Services (监控服务)
# ============================================================================
from .monitoring import HealthCheckService

# ============================================================================
# Public API - 对外暴露的服务接口
# ============================================================================
__all__ = [
    # ========== Model Domain ==========
    "ModelService",
    "ModelQueryService",
    "model_query_service",
    "ModelsCacheManager",
    "models_cache",
    "ModelProviderService",
    # ========== Capability Domain ==========
    "CapabilityService",
    "capability_service",
    # ========== Provider Domain ==========
    "ProviderService",
    # ========== Infrastructure Services ==========
    "ServiceFactory",
    "ServiceManager",
    # ========== Database Services ==========
    "db_service",
    "async_db_service",
    "sqlmodel_db_service",
    # ========== Adapter Services ==========
    "adapter_manager",
    "AdapterFactory",
    "AdapterPool",
    # ========== Load Balancing Services ==========
    "LoadBalancingStrategy",
    "LoadBalancingStrategyManager",
    "SmartRouter",
    # ========== Monitoring Services ==========
    "HealthCheckService",
]
