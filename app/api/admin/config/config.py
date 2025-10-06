"""
配置管理API端点
提供配置热重载和管理功能
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from pydantic import BaseModel

from app.core.config_hot_reload import config_hot_reload_manager, reload_config
from app.utils.simple_auth import require_api_key
from app.utils.logging_config import get_factory_logger
from app.models import ApiResponse

logger = get_factory_logger()

config_router = APIRouter(tags=["Config Management"])


class ConfigReloadResponse(BaseModel):
    """配置重载响应"""

    success: bool
    message: str
    timestamp: float
    details: Dict[str, Any]


class ConfigStatusResponse(BaseModel):
    """配置状态响应"""

    is_watching: bool
    last_reload_time: float
    watched_files: list
    callbacks_count: int
    callbacks: list


@config_router.post("/reload", response_model=ConfigReloadResponse)
async def reload_configuration(api_key: str = Depends(require_api_key)):
    """手动重载配置"""
    try:
        logger.info("📡 收到配置重载请求")
        result = await reload_config()

        return ConfigReloadResponse(
            success=result["success"],
            message="配置重载成功" if result["success"] else "配置重载失败",
            timestamp=result["timestamp"],
            details=result,
        )

    except Exception as e:
        logger.error(f"❌ 配置重载API异常: {e}")
        raise HTTPException(status_code=500, detail=f"配置重载失败: {str(e)}")


@config_router.get("/status", response_model=ConfigStatusResponse)
async def get_config_status(api_key: str = Depends(require_api_key)):
    """获取配置热重载状态"""
    try:
        status = config_hot_reload_manager.get_status()

        return ConfigStatusResponse(
            is_watching=status["is_watching"],
            last_reload_time=status["last_reload_time"],
            watched_files=status["watched_files"],
            callbacks_count=status["callbacks_count"],
            callbacks=status["callbacks"],
        )

    except Exception as e:
        logger.error(f"❌ 获取配置状态异常: {e}")
        raise HTTPException(status_code=500, detail=f"获取配置状态失败: {str(e)}")


@config_router.post("/watch/start", response_model=ApiResponse[dict])
async def start_config_watching(
    api_key: str = Depends(require_api_key),
) -> ApiResponse[dict]:
    """启动配置文件监控"""
    try:
        if config_hot_reload_manager.is_watching:
            return ApiResponse.success(
                data={"status": "already_running"}, message="配置文件监控已在运行"
            )

        # 在后台启动监控
        import asyncio

        asyncio.create_task(config_hot_reload_manager.start_watching())

        return ApiResponse.success(
            data={"status": "started"}, message="配置文件监控已启动"
        )

    except Exception as e:
        logger.error(f"❌ 启动配置监控异常: {e}")
        raise HTTPException(status_code=500, detail=f"启动配置监控失败: {str(e)}")


# @config_router.post("/watch/stop", response_model=ApiResponse[dict])
# async def stop_config_watching(
#     api_key: str = Depends(require_api_key),
# ) -> ApiResponse[dict]:
#     """停止配置文件监控"""
#     try:
#         await config_hot_reload_manager.stop_watching()
#         return ApiResponse.success(
#             data={"status": "stopped"}, message="配置文件监控已停止"
#         )

#     except Exception as e:
#         logger.error(f"❌ 停止配置监控异常: {e}")
#         raise HTTPException(status_code=500, detail=f"停止配置监控失败: {str(e)}")
