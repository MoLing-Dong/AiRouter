import time
from fastapi import APIRouter, HTTPException
from app.services import adapter_manager

health_router = APIRouter(prefix="/v1/health", tags=["健康检查"])


@health_router.get("/")
async def health_check():
    """检查所有可用模型的健康状态"""
    try:
        # 获取所有可用模型
        available_models = adapter_manager.get_available_models()

        # 检查所有模型的健康状态
        all_health_status = {}
        total_healthy_models = 0
        total_models = len(available_models)

        for model_name in available_models:
            try:
                # 获取单个模型的健康状态
                model_health = await adapter_manager.health_check_model(model_name)

                # 计算该模型的整体健康状态
                healthy_providers = sum(
                    1 for status in model_health.values() if status == "healthy"
                )
                total_providers = len(model_health)

                model_status = (
                    "healthy" if healthy_providers == total_providers else "degraded"
                )
                if healthy_providers == 0:
                    model_status = "unhealthy"

                if model_status == "healthy":
                    total_healthy_models += 1

                all_health_status[model_name] = {
                    "status": model_status,
                    "providers": model_health,
                    "healthy_providers": healthy_providers,
                    "total_providers": total_providers,
                }

            except Exception as e:
                logger.info(f"检查模型 {model_name} 健康状态时出错: {e}")
                all_health_status[model_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "providers": {},
                    "healthy_providers": 0,
                    "total_providers": 0,
                }

        # 计算整体健康状态
        overall_status = (
            "healthy" if total_healthy_models == total_models else "degraded"
        )
        if total_healthy_models == 0:
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "models": all_health_status,
            "healthy_models": total_healthy_models,
            "total_models": total_models,
            "use_database": adapter_manager.use_database,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@health_router.get("/models")
async def get_models_health():
    """获取所有模型的健康状态概览"""
    try:
        available_models = adapter_manager.get_available_models()
        models_health = {}

        for model_name in available_models:
            try:
                model_health = await adapter_manager.health_check_model(model_name)
                healthy_count = sum(
                    1 for status in model_health.values() if status == "healthy"
                )
                total_count = len(model_health)

                status = "healthy" if healthy_count == total_count else "degraded"
                if healthy_count == 0:
                    status = "unhealthy"

                models_health[model_name] = {
                    "status": status,
                    "healthy_providers": healthy_count,
                    "total_providers": total_count,
                }
            except Exception as e:
                models_health[model_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "healthy_providers": 0,
                    "total_providers": 0,
                }

        return {
            "timestamp": time.time(),
            "models": models_health,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型健康状态失败: {str(e)}")


@health_router.get("/models/{model_name}")
async def get_model_health(model_name: str):
    """获取单个模型的详细健康状态"""
    try:
        # 检查模型是否存在
        available_models = adapter_manager.get_available_models()
        if model_name not in available_models:
            raise HTTPException(status_code=404, detail=f"模型不存在: {model_name}")

        # 获取模型的健康状态
        health_status = await adapter_manager.health_check_model(model_name)

        # 计算该模型的整体健康状态
        healthy_count = sum(
            1 for status in health_status.values() if status == "healthy"
        )
        total_count = len(health_status)

        overall_status = "healthy" if healthy_count == total_count else "degraded"
        if healthy_count == 0:
            overall_status = "unhealthy"

        return {
            "model_name": model_name,
            "status": overall_status,
            "timestamp": time.time(),
            "providers": health_status,
            "healthy_providers": healthy_count,
            "total_providers": total_count,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"检查模型健康状态失败: {str(e)}")


@health_router.get("/providers")
async def get_providers_health():
    """获取所有提供商的健康状态"""
    try:
        available_models = adapter_manager.get_available_models()
        providers_health = {}

        for model_name in available_models:
            try:
                adapters = adapter_manager.get_model_adapters(model_name)
                for adapter in adapters:
                    provider_name = adapter.provider
                    if provider_name not in providers_health:
                        providers_health[provider_name] = {
                            "models": [],
                            "health_status": getattr(
                                adapter, "health_status", "unknown"
                            ),
                            "base_url": adapter.base_url,
                        }

                    providers_health[provider_name]["models"].append(model_name)
            except Exception as e:
                logger.info(f"获取模型 {model_name} 的提供商信息时出错: {e}")
                continue

        return {
            "timestamp": time.time(),
            "providers": providers_health,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商健康状态失败: {str(e)}")
