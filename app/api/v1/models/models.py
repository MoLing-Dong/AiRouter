import time
from fastapi import APIRouter, HTTPException
from app.core.adapters import adapter_manager

models_router = APIRouter(prefix="/v1/models", tags=["模型管理"])


@models_router.get("/")
async def list_models():
    """获取可用模型列表"""
    try:
        models = []
        # 直接从适配器管理器获取可用模型
        available_models = adapter_manager.get_available_models()

        for model_name in available_models:
            try:
                adapters = adapter_manager.get_model_adapters(model_name)
                if adapters:

                    # 获取所有可用的提供商
                    providers = [adapter.provider for adapter in adapters]
                    models.append(
                        {
                            "id": model_name,
                            "object": "model",
                            "created": int(time.time()),
                            "permission": providers,
                            "root": model_name,
                            "parent": None,
                            "providers_count": len(adapters),
                        }
                    )
            except Exception as e:
                print(f"处理模型 {model_name} 时出错: {e}")
                continue

        return {"object": "list", "data": models}
    except Exception as e:
        print(f"获取模型列表失败: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取模型列表失败: {str(e)}")


@models_router.get("/{model_name}/health")
async def check_model_health(model_name: str):
    """检查单个模型的健康状态"""
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


@models_router.get("/{model_name}")
async def get_model_details(model_name: str):
    """获取单个模型的详细信息"""
    try:
        # 检查模型是否存在
        available_models = adapter_manager.get_available_models()
        if model_name not in available_models:
            raise HTTPException(status_code=404, detail=f"模型不存在: {model_name}")

        # 获取模型配置
        model_config = adapter_manager.get_model_config(model_name)
        if not model_config:
            raise HTTPException(status_code=404, detail=f"模型配置不存在: {model_name}")

        # 获取模型的所有适配器
        adapters = adapter_manager.get_model_adapters(model_name)

        # 构建提供商信息
        providers = []
        for adapter in adapters:
            providers.append(
                {
                    "name": adapter.provider,
                    "base_url": adapter.base_url,
                    "weight": getattr(adapter, "weight", 1.0),
                    "health_status": (
                        adapter.health_status.value
                        if hasattr(adapter, "health_status")
                        else "unknown"
                    ),
                    "metrics": (
                        {
                            "response_time": adapter.metrics.response_time,
                            "success_rate": adapter.metrics.success_rate,
                            "cost_per_1k_tokens": adapter.metrics.cost_per_1k_tokens,
                            "total_requests": adapter.metrics.total_requests,
                            "total_tokens": adapter.metrics.total_tokens,
                        }
                        if hasattr(adapter, "metrics")
                        else {}
                    ),
                }
            )

        return {
            "model_name": model_name,
            "model_type": model_config.model_type,
            "max_tokens": model_config.max_tokens,
            "temperature": model_config.temperature,
            "top_p": model_config.top_p,
            "frequency_penalty": model_config.frequency_penalty,
            "presence_penalty": model_config.presence_penalty,
            "enabled": model_config.enabled,
            "priority": model_config.priority,
            "providers": providers,
            "providers_count": len(providers),
            "created_at": time.time(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取模型详细信息失败: {str(e)}")
