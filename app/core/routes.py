from fastapi import APIRouter
from app.api.v1 import (
    chat_router, 
    models_router, 
    stats_router, 
    db_router, 
    health_router,
    providers_router
)
from app.api.v1.load_balancing import router as load_balancing_router


def register_routes(app):
    """注册所有路由"""
    
    # 注册v1版本路由 - 这些路由已经包含了/v1前缀
    app.include_router(chat_router, tags=["聊天"])
    app.include_router(models_router, tags=["模型管理"])
    app.include_router(stats_router, tags=["统计"])
    app.include_router(db_router, tags=["数据库管理"])
    app.include_router(health_router, tags=["健康检查"])
    
    # 注册提供商管理路由
    app.include_router(providers_router, tags=["提供商管理"])
    
    # 注册负载均衡策略管理路由
    app.include_router(load_balancing_router, tags=["负载均衡策略"])
