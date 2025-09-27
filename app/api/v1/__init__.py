# Export all v1 version routes
from fastapi import APIRouter
from .chat import chat_router
from .image import image_router
from .anthropic import anthropic_router

# 创建v1主路由
v1_router = APIRouter(prefix="/v1", tags=["V1 API"])

# 注册核心AI服务路由
v1_router.include_router(chat_router, tags=["Chat"])
v1_router.include_router(image_router, tags=["Images"])
v1_router.include_router(anthropic_router, tags=["Anthropic"])

# 导出所有路由器
__all__ = ["v1_router", "chat_router", "image_router", "anthropic_router"]
