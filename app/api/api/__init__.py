"""
API Module
其他业务相关的API接口，包括认证、数据库操作、负载均衡等
"""

from fastapi import APIRouter

# auth目录为空，暂时注释
# from .auth import auth_router
from .database import db_router
from .load_balancing import router as load_balancing_router
from .pool import pool_router

# 创建api主路由
api_router = APIRouter(prefix="/api", tags=["API"])

# 注册子路由
# api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(db_router, prefix="/database", tags=["Database"])
api_router.include_router(
    load_balancing_router, prefix="/load-balancing", tags=["Load Balancing"]
)
api_router.include_router(pool_router, prefix="/pool", tags=["Pool Management"])

# 导出
__all__ = ["api_router"]
