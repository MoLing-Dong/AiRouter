"""
Admin API Module
管理相关的API接口，包括模型管理、健康检查、统计信息等
"""

from fastapi import APIRouter
from .health import health_router
from .models import models_router
from .stats import stats_router
from .monitoring import monitoring_router

# 处理providers.py (单文件，不是目录)
from .providers import providers_router

# 创建admin主路由
admin_router = APIRouter(prefix="/admin", tags=["Admin"])

# 注册子路由
admin_router.include_router(health_router, prefix="/health", tags=["Health"])
admin_router.include_router(models_router, prefix="/models", tags=["Models"])
admin_router.include_router(stats_router, prefix="/stats", tags=["Stats"])
admin_router.include_router(
    monitoring_router, prefix="/monitoring", tags=["Monitoring"]
)
admin_router.include_router(providers_router, prefix="/providers", tags=["Providers"])

# 导出
__all__ = ["admin_router"]
