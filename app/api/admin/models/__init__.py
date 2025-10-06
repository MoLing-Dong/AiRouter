"""
模型管理模块
提供模型列表、健康检查、能力管理等功能
"""

from .models import models_router

# 服务层已按领域重组
from app.services.model import (
    models_cache,
    ModelsCacheManager,
    model_query_service as model_service,
    ModelQueryService,
)
from app.services.capability import (
    capability_service,
    CapabilityService,
)

__all__ = [
    # 路由
    "models_router",
    # 缓存管理
    "models_cache",
    "ModelsCacheManager",
    # 模型查询服务
    "model_service",
    "ModelQueryService",
    # 能力管理服务
    "capability_service",
    "CapabilityService",
]
