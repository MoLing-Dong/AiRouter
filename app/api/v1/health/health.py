import time
import asyncio
from fastapi import APIRouter, HTTPException, Query
from app.services import adapter_manager
from app.utils.logging_config import get_factory_logger

health_router = APIRouter(prefix="/v1/health", tags=["Health Check"])

# Get logger
logger = get_factory_logger()


@health_router.get("/")
async def health_check(
    timeout: float = Query(30.0, description="Health check timeout in seconds"),
    use_concurrent: bool = Query(True, description="Use concurrent health checking"),
):
    """Check all available models' health status concurrently"""
    try:
        start_time = time.time()

        # Get all available models
        available_models = adapter_manager.get_available_models()

        if not available_models:
            return {
                "status": "healthy",
                "timestamp": time.time(),
                "models": {},
                "healthy_models": 0,
                "total_models": 0,
                "use_database": adapter_manager.use_database,
                "execution_time": 0.0,
                "concurrent": False,
            }

        # Check all models' health status
        if use_concurrent:
            try:
                # 使用并发健康检查
                all_health_status = (
                    await adapter_manager.health_checker.check_all_models_with_timeout(
                        available_models,
                        adapter_manager.model_adapters,
                        timeout=timeout,
                    )
                )
                concurrent = True
            except Exception as e:
                logger.warning(
                    f"Concurrent health check failed, falling back to sequential: {e}"
                )
                # 回退到串行执行
                all_health_status = await adapter_manager.health_check_all()
                concurrent = False
        else:
            # 使用串行健康检查
            all_health_status = await adapter_manager.health_check_all()
            concurrent = False

        execution_time = time.time() - start_time

        # Calculate overall health status for each model
        models_summary = {}
        total_healthy_models = 0
        total_models = len(available_models)

        for model_name in available_models:
            try:
                # 提取该模型的提供商健康状态
                model_providers = {}
                for key, status in all_health_status.items():
                    if key.startswith(f"{model_name}:"):
                        provider_name = key.split(":", 1)[1]
                        model_providers[provider_name] = status

                # 计算模型整体健康状态
                healthy_providers = sum(
                    1 for status in model_providers.values() if status == "healthy"
                )
                total_providers = len(model_providers)

                if total_providers == 0:
                    model_status = "unknown"
                elif healthy_providers == total_providers:
                    model_status = "healthy"
                    total_healthy_models += 1
                elif healthy_providers == 0:
                    model_status = "unhealthy"
                else:
                    model_status = "degraded"

                models_summary[model_name] = {
                    "status": model_status,
                    "providers": model_providers,
                    "healthy_providers": healthy_providers,
                    "total_providers": total_providers,
                }

            except Exception as e:
                logger.info(f"Error processing model {model_name} health status: {e}")
                models_summary[model_name] = {
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
            "models": models_summary,
            "healthy_models": total_healthy_models,
            "total_models": total_models,
            "use_database": adapter_manager.use_database,
            "execution_time": execution_time,
            "concurrent": concurrent,
            "timeout": timeout,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@health_router.get("/models/{model_name}")
async def get_model_health(
    model_name: str,
    timeout: float = Query(10.0, description="Health check timeout in seconds"),
    use_concurrent: bool = Query(True, description="Use concurrent health checking"),
):
    """Get single model's detailed health status"""
    try:
        start_time = time.time()

        # Check if model exists
        available_models = adapter_manager.get_available_models()
        if model_name not in available_models:
            raise HTTPException(
                status_code=404, detail=f"Model does not exist: {model_name}"
            )

        # Get model's health status
        if use_concurrent:
            try:
                health_status = await adapter_manager.health_checker.check_model_health_with_timeout(
                    model_name,
                    adapter_manager.get_model_adapters(model_name),
                    timeout=timeout,
                )
                concurrent = True
            except Exception as e:
                logger.warning(
                    f"Concurrent health check failed, falling back to sequential: {e}"
                )
                health_status = await adapter_manager.health_check_model(model_name)
                concurrent = False
        else:
            health_status = await adapter_manager.health_check_model(model_name)
            concurrent = False

        execution_time = time.time() - start_time

        # Calculate overall health status for the model
        healthy_count = sum(
            1 for status in health_status.values() if status == "healthy"
        )
        total_count = len(health_status)

        if total_count == 0:
            overall_status = "unknown"
        elif healthy_count == total_count:
            overall_status = "healthy"
        elif healthy_count == 0:
            overall_status = "unhealthy"
        else:
            overall_status = "degraded"

        return {
            "model_name": model_name,
            "status": overall_status,
            "timestamp": time.time(),
            "providers": health_status,
            "healthy_providers": healthy_count,
            "total_providers": total_count,
            "execution_time": execution_time,
            "concurrent": concurrent,
            "timeout": timeout,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Check model health status failed: {str(e)}"
        )


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
                logger.info(
                    f"Error getting provider information for model {model_name}: {e}"
                )
                continue

        return {
            "timestamp": time.time(),
            "providers": providers_health,
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get provider health status failed: {str(e)}"
        )


@health_router.get("/performance")
async def get_health_check_performance():
    """Get health check performance metrics"""
    try:
        available_models = adapter_manager.get_available_models()

        # 测试并发健康检查性能
        start_time = time.time()
        concurrent_result = (
            await adapter_manager.health_checker.check_all_models_with_timeout(
                available_models, adapter_manager.model_adapters, timeout=30.0
            )
        )
        concurrent_time = time.time() - start_time

        # 测试串行健康检查性能
        start_time = time.time()
        sequential_result = (
            await adapter_manager.health_checker._check_all_models_sequential(
                available_models, adapter_manager.model_adapters
            )
        )
        sequential_time = time.time() - start_time

        # 计算性能提升
        if sequential_time > 0:
            speedup = sequential_time / concurrent_time
            improvement_percent = (
                (sequential_time - concurrent_time) / sequential_time
            ) * 100
        else:
            speedup = 1.0
            improvement_percent = 0.0

        return {
            "timestamp": time.time(),
            "performance_metrics": {
                "concurrent_time": concurrent_time,
                "sequential_time": sequential_time,
                "speedup": speedup,
                "improvement_percent": improvement_percent,
                "total_models": len(available_models),
                "total_adapters": sum(
                    len(adapters)
                    for adapters in adapter_manager.model_adapters.values()
                ),
            },
            "concurrent_result_count": len(concurrent_result),
            "sequential_result_count": len(sequential_result),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get performance metrics failed: {str(e)}"
        )
