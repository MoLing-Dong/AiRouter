import time
import traceback
from typing import Optional
from fastapi import APIRouter, HTTPException
from app.services import adapter_manager
from app.utils.logging_config import get_factory_logger

models_router = APIRouter(prefix="/v1/models", tags=["Model Management"])

# Get logger
logger = get_factory_logger()


@models_router.get("/")
async def list_models(capabilities: Optional[str] = None):
    """Get available model list with optional capability filtering
    
    Args:
        capabilities: Comma-separated list of capability names to filter by.
                     Examples: "TEXT", "TEXT,MULTIMODAL_IMAGE_UNDERSTANDING", "TEXT_TO_IMAGE"
                     If not provided, returns all models
    """
    try:
        models = []
        
        # Parse capabilities parameter
        capability_list = None
        if capabilities:
            capability_list = [cap.strip() for cap in capabilities.split(",")]
            logger.info(f"Filtering models by capabilities: {capability_list}")
        
        # Get available model list from adapter manager with capability filtering
        available_models = adapter_manager.get_available_models(capabilities=capability_list)

        for model_name in available_models:
            try:
                adapters = adapter_manager.get_model_adapters(model_name)
                if adapters:

                    # Get all available providers
                    providers = [adapter.provider for adapter in adapters]

                    # Get model capabilities from database
                    capabilities = []
                    try:
                        from app.services.database_service import db_service

                        # Get model by name to get ID
                        model = db_service.get_model_by_name(model_name)
                        if model:
                            capabilities = db_service.get_model_capabilities(model.id)
                    except Exception as e:
                        logger.info(
                            f"Error getting capabilities for model {model_name}: {e}"
                        )
                        # Capability retrieval failure does not affect model information return

                    models.append(
                        {
                            "id": model_name,
                            "object": "model",
                            "created": int(time.time()),
                            "permission": providers,
                            "root": model_name,
                            "parent": None,
                            "providers_count": len(adapters),
                            "capabilities": capabilities,
                            "capabilities_count": len(capabilities),
                        }
                    )
            except Exception as e:
                logger.info(f"Error processing model {model_name}: {e}")
                continue

        return {"object": "list", "data": models}
    except Exception as e:
        logger.info(f"Get model list failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Get model list failed: {str(e)}")


# 具体的路径必须放在动态路径之前，避免路由冲突
@models_router.get("/capabilities")
async def get_all_capabilities():
    """Get all available capabilities"""
    try:
        from app.services.database_service import db_service

        capabilities = db_service.get_all_capabilities()

        return {
            "object": "list",
            "data": capabilities,
            "total_capabilities": len(capabilities),
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.info(f"Get all capabilities failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Get all capabilities failed: {str(e)}"
        )


@models_router.get("/all/details")
async def get_all_models_details():
    """Get all models' detailed information from database"""
    try:
        all_models_details = []

        # Get all models from database, not just available models
        from app.services.database_service import db_service

        # Get all models (including disabled ones)
        all_models = db_service.get_all_models(is_enabled=None)

        for model in all_models:
            try:
                # Get all provider associations for the model (including disabled ones)
                model_providers = db_service.get_model_providers(
                    model.id, is_enabled=None
                )

                # Build provider information
                providers = []
                for mp in model_providers:
                    # Get provider information (including disabled ones)
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

                    # Add metrics information (if available)
                    if hasattr(mp, "response_time_avg"):
                        provider_info["response_time_avg"] = mp.response_time_avg
                    if hasattr(mp, "success_rate"):
                        provider_info["success_rate"] = mp.success_rate

                    providers.append(provider_info)

                # Calculate overall health status
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

                # Build model detailed information
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

                # Get model parameters (if available)
                try:
                    model_params = db_service.get_model_params(
                        model.id, is_enabled=None
                    )
                    if model_params:
                        model_detail["parameters"] = [
                            {
                                "key": param.param_key,
                                "value": param.param_value,
                                "enabled": param.is_enabled,
                            }
                            for param in model_params
                        ]
                except Exception as e:
                    logger.info(f"Error getting parameters for model {model.name}: {e}")

                # Get model capabilities (if available)
                try:
                    model_capabilities = db_service.get_model_capabilities(model.id)
                    if model_capabilities:
                        model_detail["capabilities"] = [
                            {
                                "id": cap["capability_id"],
                                "name": cap["capability_name"],
                                "description": cap["description"],
                            }
                            for cap in model_capabilities
                        ]
                except Exception as e:
                    logger.info(f"Error getting capabilities for model {model.name}: {e}")

                all_models_details.append(model_detail)

            except Exception as e:
                logger.info(f"Error processing model {model.name}: {e}")
                continue

        return {
            "object": "list",
            "data": all_models_details,
            "total_models": len(all_models_details),
            "timestamp": time.time(),
        }
    except Exception as e:
        logger.info(f"Get all models' detailed information failed: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Get all models' detailed information failed: {str(e)}",
        )


@models_router.get("/{model_name}/health")
async def check_model_health(model_name: str):
    """Check single model's health status"""
    try:
        # Check if model exists
        available_models = adapter_manager.get_available_models()
        if model_name not in available_models:
            raise HTTPException(
                status_code=404, detail=f"Model does not exist: {model_name}"
            )

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
        raise HTTPException(
            status_code=500, detail=f"Check model health status failed: {str(e)}"
        )


@models_router.get("/{model_name}")
async def get_model_details(model_name: str):
    """Get single model's detailed information"""
    try:
        # Check if model exists
        available_models = adapter_manager.get_available_models()
        if model_name not in available_models:
            raise HTTPException(
                status_code=404, detail=f"Model does not exist: {model_name}"
            )

        # Get model configuration
        model_config = adapter_manager.get_model_config(model_name)
        if not model_config:
            raise HTTPException(
                status_code=404,
                detail=f"Model configuration does not exist: {model_name}",
            )

        # Get all adapters for the model
        adapters = adapter_manager.get_model_adapters(model_name)

        # Build provider information
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

        # Get model capabilities from database
        capabilities = []
        try:
            from app.services.database_service import db_service

            # Get model by name to get ID
            model = db_service.get_model_by_name(model_name)
            if model:
                capabilities = db_service.get_model_capabilities(model.id)
        except Exception as e:
            logger.info(f"Error getting capabilities for model {model_name}: {e}")
            # Capability retrieval failure does not affect model information return

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
            "capabilities": capabilities,
            "capabilities_count": len(capabilities),
            "created_at": time.time(),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get model detailed information failed: {str(e)}"
        )



@models_router.get("/{model_name}/capabilities")
async def get_model_capabilities(model_name: str):
    """Get specific model capabilities"""
    try:
        from app.services.database_service import db_service

        # Get model by name to get ID
        model = db_service.get_model_by_name(model_name)
        if not model:
            raise HTTPException(
                status_code=404, detail=f"Model does not exist: {model_name}"
            )

        capabilities = db_service.get_model_capabilities(model.id)

        return {
            "model_name": model_name,
            "model_id": model.id,
            "capabilities": capabilities,
            "capabilities_count": len(capabilities),
            "timestamp": time.time(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Get model capabilities failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Get model capabilities failed: {str(e)}"
        )


@models_router.post("/{model_name}/capabilities")
async def add_model_capability(model_name: str, capability_name: str):
    """Add capability to model"""
    try:
        from app.services.database_service import db_service

        # Get model by name to get ID
        model = db_service.get_model_by_name(model_name)
        if not model:
            raise HTTPException(
                status_code=404, detail=f"Model does not exist: {model_name}"
            )

        success = db_service.add_model_capability(model.id, capability_name)

        if success:
            return {
                "message": f"Capability {capability_name} added to model {model_name}",
                "model_name": model_name,
                "capability_name": capability_name,
                "timestamp": time.time(),
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to add capability {capability_name} to model {model_name}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Add model capability failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Add model capability failed: {str(e)}"
        )


@models_router.delete("/{model_name}/capabilities/{capability_name}")
async def remove_model_capability(model_name: str, capability_name: str):
    """Remove capability from model"""
    try:
        from app.services.database_service import db_service

        # Get model by name to get ID
        model = db_service.get_model_by_name(model_name)
        if not model:
            raise HTTPException(
                status_code=404, detail=f"Model does not exist: {model_name}"
            )

        success = db_service.remove_model_capability(model.id, capability_name)

        if success:
            return {
                "message": f"Capability {capability_name} removed from model {model_name}",
                "model_name": model_name,
                "capability_name": capability_name,
                "timestamp": time.time(),
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to remove capability {capability_name} from model {model_name}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.info(f"Remove model capability failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Remove model capability failed: {str(e)}"
        )
