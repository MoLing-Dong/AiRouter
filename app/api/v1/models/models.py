import time
from fastapi import APIRouter, HTTPException
from app.services import adapter_manager
from app.utils.logging_config import get_factory_logger

models_router = APIRouter(prefix="/v1/models", tags=["模型管理"])

# 获取日志器
logger = get_factory_logger()


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
                logger.info(f"处理模型 {model_name} 时出错: {e}")
                continue

        return {"object": "list", "data": models}
    except Exception as e:
        logger.info(f"获取模型列表失败: {e}")
        import traceback

        traceback.logger.info_exc()
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


@models_router.get("/all/details")
async def get_all_models_details():
    """获取数据库中所有模型的详细信息"""
    try:
        all_models_details = []

        # 从数据库获取所有模型，而不是仅获取可用的模型
        from app.services.database_service import db_service

        # 获取所有模型（包括禁用的）
        all_models = db_service.get_all_models(is_enabled=None)

        for model in all_models:
            try:
                # 获取模型的所有提供商关联（包括禁用的）
                model_providers = db_service.get_model_providers(
                    model.id, is_enabled=None
                )

                # 构建提供商信息
                providers = []
                for mp in model_providers:
                    # 获取提供商信息（包括禁用的）
                    provider = db_service.get_provider_by_id(
                        mp.provider_id, is_enabled=None
                    )
                    if not provider:
                        continue

                    provider_info = {
                        "id": provider.id,
                        "name": provider.name,
                        "provider_type": provider.provider_type,
                        "base_url": provider.official_endpoint
                        or provider.third_party_endpoint,
                        "weight": mp.weight,
                        "priority": mp.priority,
                        "health_status": mp.health_status,
                        "is_enabled": mp.is_enabled,
                        "is_preferred": mp.is_preferred,
                        "cost_per_1k_tokens": mp.cost_per_1k_tokens,
                        "overall_score": mp.overall_score,
                    }

                    # 添加指标信息（如果可用）
                    if hasattr(mp, "response_time_avg"):
                        provider_info["response_time_avg"] = mp.response_time_avg
                    if hasattr(mp, "success_rate"):
                        provider_info["success_rate"] = mp.success_rate

                    providers.append(provider_info)

                # 计算整体健康状态
                healthy_count = sum(
                    1 for p in providers if p.get("health_status") == "healthy"
                )
                total_count = len(providers)

                overall_status = (
                    "healthy" if healthy_count == total_count else "degraded"
                )
                if healthy_count == 0:
                    overall_status = "unhealthy"
                if total_count == 0:
                    overall_status = "no_providers"

                # 构建模型详细信息
                model_detail = {
                    "id": model.id,
                    "model_name": model.name,
                    "llm_type": model.llm_type.value if model.llm_type else None,
                    "description": model.description,
                    "enabled": model.is_enabled,
                    "overall_health": overall_status,
                    "providers": providers,
                    "providers_count": len(providers),
                    "healthy_providers": healthy_count,
                    "created_at": (
                        model.created_at.timestamp()
                        if model.created_at
                        else time.time()
                    ),
                    "updated_at": (
                        model.updated_at.timestamp()
                        if model.updated_at
                        else time.time()
                    ),
                }

                # 获取模型参数（如果有的话）
                try:
                    model_params = db_service.get_model_params(
                        model.id, is_enabled=None
                    )
                    if model_params:
                        params_dict = {}
                        for param in model_params:
                            if param.param_key and param.param_value is not None:
                                params_dict[param.param_key] = param.param_value

                        if params_dict:
                            model_detail["parameters"] = params_dict
                except Exception as e:
                    logger.info(f"获取模型 {model.name} 参数时出错: {e}")
                    # 参数获取失败不影响模型信息返回

                all_models_details.append(model_detail)

            except Exception as e:
                logger.info(f"处理模型 {model.name} 详细信息时出错: {e}")
                continue

        return {
            "object": "list",
            "data": all_models_details,
            "total_models": len(all_models_details),
            "timestamp": time.time(),
        }

    except Exception as e:
        logger.info(f"获取所有模型详细信息失败: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"获取所有模型详细信息失败: {str(e)}"
        )
