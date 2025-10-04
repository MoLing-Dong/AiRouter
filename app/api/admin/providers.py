from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import ApiResponse

# Get logger
logger = get_factory_logger()

providers_router = APIRouter(tags=["Provider Management"])


@providers_router.get("/", response_model=ApiResponse[dict])
async def get_all_providers() -> ApiResponse[dict]:
    """Get all providers and their health status"""
    try:
        providers = db_service.get_all_providers()
        providers_list = [
            {
                "id": provider.id,
                "name": provider.name,
                "provider_type": provider.provider_type,
                "official_endpoint": provider.official_endpoint,
                "is_enabled": provider.is_enabled,
                "description": provider.description,
            }
            for provider in providers
        ]
        return ApiResponse.success(
            data={"providers": providers_list}, message="获取提供商列表成功"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get provider list failed: {str(e)}"
        )


@providers_router.get("/{provider_name}/health", response_model=ApiResponse[dict])
async def get_provider_health(provider_name: str) -> ApiResponse[dict]:
    """Get specified provider's health status"""
    try:
        health_info = db_service.get_provider_health_status(provider_name)
        if not health_info:
            raise HTTPException(
                status_code=404, detail=f"Provider {provider_name} does not exist"
            )

        return ApiResponse.success(data=health_info, message="获取提供商健康状态成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get provider health status failed: {str(e)}"
        )


@providers_router.get("/{provider_name}/performance", response_model=ApiResponse[dict])
async def get_provider_performance(provider_name: str) -> ApiResponse[dict]:
    """Get specified provider's performance statistics"""
    try:
        performance_stats = db_service.get_provider_performance_stats(provider_name)
        if not performance_stats:
            raise HTTPException(
                status_code=404, detail=f"Provider {provider_name} does not exist"
            )

        return ApiResponse.success(
            data=performance_stats, message="获取提供商性能统计成功"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Get provider performance statistics failed: {str(e)}",
        )


@providers_router.get("/recommendations", response_model=ApiResponse[dict])
async def get_provider_recommendations(
    model_name: Optional[str] = Query(None),
) -> ApiResponse[dict]:
    """Get provider recommendations"""
    try:
        recommendations = db_service.get_provider_recommendations(model_name)
        result = {
            "model_name": model_name,
            "recommendations": [
                {
                    "provider_name": rec["provider"].name,
                    "provider_type": rec["provider"].provider_type,
                    "score": rec["score"],
                    "health_status": rec["health_status"],
                    "response_time": rec["response_time"],
                    "success_rate": rec["success_rate"],
                    "cost_per_1k_tokens": rec["cost_per_1k_tokens"],
                    "reason": rec["reason"],
                }
                for rec in recommendations
            ],
        }
        return ApiResponse.success(data=result, message="获取提供商推荐成功")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get provider recommendations failed: {str(e)}"
        )


@providers_router.get(
    "/{provider_name}/best-for-model", response_model=ApiResponse[dict]
)
async def get_best_provider_for_model(model_name: str) -> ApiResponse[dict]:
    """Get best provider for specified model"""
    try:
        best_provider = db_service.get_best_provider_for_model(model_name)
        if not best_provider:
            raise HTTPException(
                status_code=404, detail=f"Model {model_name} has no available provider"
            )

        result = {
            "model_name": model_name,
            "best_provider": {
                "id": best_provider.id,
                "name": best_provider.name,
                "provider_type": best_provider.provider_type,
                "official_endpoint": best_provider.official_endpoint,
            },
        }
        return ApiResponse.success(data=result, message="获取最佳提供商成功")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get best provider for model failed: {str(e)}"
        )


@providers_router.put("/{provider_name}/health", response_model=ApiResponse[None])
async def update_provider_health(
    provider_name: str, health_status: str
) -> ApiResponse[None]:
    """Update provider's health status"""
    try:
        if health_status not in ["healthy", "degraded", "unhealthy"]:
            raise HTTPException(
                status_code=400,
                detail="Health status must be healthy, degraded or unhealthy",
            )

        success = db_service.update_provider_health_status(provider_name, health_status)
        if not success:
            raise HTTPException(
                status_code=404, detail=f"Provider {provider_name} does not exist"
            )

        return ApiResponse.success(
            message=f"Provider {provider_name}'s health status has been updated to {health_status}"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Update provider health status failed: {str(e)}"
        )


@providers_router.get("/stats/overview", response_model=ApiResponse[dict])
async def get_providers_overview() -> ApiResponse[dict]:
    """Get provider overview statistics"""
    try:
        providers_with_health = db_service.get_all_providers_with_health()

        total_providers = len(providers_with_health)
        healthy_providers = len(
            [
                p
                for p in providers_with_health
                if p["health_info"]["overall_health"] == "healthy"
            ]
        )
        degraded_providers = len(
            [
                p
                for p in providers_with_health
                if p["health_info"]["overall_health"] == "degraded"
            ]
        )
        unhealthy_providers = len(
            [
                p
                for p in providers_with_health
                if p["health_info"]["overall_health"] == "unhealthy"
            ]
        )

        avg_score = (
            sum(p["health_info"]["average_score"] for p in providers_with_health)
            / total_providers
            if total_providers > 0
            else 0
        )

        overview = {
            "total_providers": total_providers,
            "healthy_providers": healthy_providers,
            "degraded_providers": degraded_providers,
            "unhealthy_providers": unhealthy_providers,
            "average_score": avg_score,
            "health_distribution": {
                "healthy_percentage": (
                    (healthy_providers / total_providers * 100)
                    if total_providers > 0
                    else 0
                ),
                "degraded_percentage": (
                    (degraded_providers / total_providers * 100)
                    if total_providers > 0
                    else 0
                ),
                "unhealthy_percentage": (
                    (unhealthy_providers / total_providers * 100)
                    if total_providers > 0
                    else 0
                ),
            },
        }
        return ApiResponse.success(data=overview, message="获取提供商概览统计成功")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get provider overview statistics failed: {str(e)}"
        )
