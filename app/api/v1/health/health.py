import time
from fastapi import APIRouter, HTTPException
from app.services import adapter_manager
from app.utils.logging_config import get_factory_logger

health_router = APIRouter(prefix="/v1/health", tags=["Health Check"])

# Get logger
logger = get_factory_logger()


@health_router.get("/")
async def health_check():
    """Check all available models' health status"""
    try:
        # Get all available models
        available_models = adapter_manager.get_available_models()

        # Check all models' health status
        all_health_status = {}
        total_healthy_models = 0
        total_models = len(available_models)

        for model_name in available_models:
            try:
                # Get single model's health status
                model_health = await adapter_manager.health_check_model(model_name)

                # Calculate overall health status for the model
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
                logger.info(f"Error checking model {model_name} health status: {e}")
                all_health_status[model_name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "providers": {},
                    "healthy_providers": 0,
                    "total_providers": 0,
                }

        # Calculate overall health status
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
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@health_router.get("/models")
async def get_models_health():
    """Get all models' health status overview"""
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
        raise HTTPException(status_code=500, detail=f"Get model health status failed: {str(e)}")


@health_router.get("/models/{model_name}")
async def get_model_health(model_name: str):
    """Get single model's detailed health status"""
    try:
        # Check if model exists
        available_models = adapter_manager.get_available_models()
        if model_name not in available_models:
            raise HTTPException(status_code=404, detail=f"Model does not exist: {model_name}")

        # Get model's health status
        health_status = await adapter_manager.health_check_model(model_name)

        # Calculate overall health status for the model
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
        raise HTTPException(status_code=500, detail=f"Check model health status failed: {str(e)}")


@health_router.get("/providers")
async def get_providers_health():
    """Get all providers' health status"""
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
                logger.info(f"Error getting provider information for model {model_name}: {e}")
                continue

        return {
            "timestamp": time.time(),
            "providers": providers_health,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get provider health status failed: {str(e)}")
