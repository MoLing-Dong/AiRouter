from fastapi import APIRouter
from app.api import chat_router, models_router, stats_router, db_router


def register_routes(app):
    """注册所有路由"""
    # 注册v1 API路由
    app.include_router(chat_router)
    app.include_router(models_router)
    app.include_router(stats_router)
    app.include_router(db_router)
