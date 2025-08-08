from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.database_service import db_service

providers_router = APIRouter(prefix="/v1/providers", tags=["提供商管理"])


@providers_router.get("/")
async def get_all_providers_with_health():
    """获取所有提供商及其健康状态"""
    try:
        providers = db_service.get_all_providers_with_health()
        return {
            "providers": [
                {
                    "id": provider["provider"].id,
                    "name": provider["provider"].name,
                    "provider_type": provider["provider"].provider_type,
                    "official_endpoint": provider["provider"].official_endpoint,
                    "third_party_endpoint": provider["provider"].third_party_endpoint,
                    "is_enabled": provider["provider"].is_enabled,
                    "health_info": provider["health_info"]
                }
                for provider in providers
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商列表失败: {str(e)}")


@providers_router.get("/top")
async def get_top_providers(limit: int = Query(5, ge=1, le=20)):
    """获取排名前几的提供商"""
    try:
        top_providers = db_service.get_top_providers(limit)
        return {
            "top_providers": [
                {
                    "rank": i + 1,
                    "provider_name": provider["provider"].name,
                    "average_score": provider["health_info"]["average_score"],
                    "overall_health": provider["health_info"]["overall_health"],
                    "total_models": provider["health_info"]["total_models"],
                    "healthy_models": provider["health_info"]["healthy_models"],
                }
                for i, provider in enumerate(top_providers)
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取顶级提供商失败: {str(e)}")


@providers_router.get("/{provider_name}/health")
async def get_provider_health(provider_name: str):
    """获取指定提供商的健康状态"""
    try:
        health_info = db_service.get_provider_health_status(provider_name)
        if not health_info:
            raise HTTPException(status_code=404, detail=f"提供商 {provider_name} 不存在")
        
        return health_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商健康状态失败: {str(e)}")


@providers_router.get("/{provider_name}/performance")
async def get_provider_performance(provider_name: str):
    """获取指定提供商的性能统计"""
    try:
        performance_stats = db_service.get_provider_performance_stats(provider_name)
        if not performance_stats:
            raise HTTPException(status_code=404, detail=f"提供商 {provider_name} 不存在")
        
        return performance_stats
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商性能统计失败: {str(e)}")


@providers_router.get("/recommendations")
async def get_provider_recommendations(model_name: Optional[str] = Query(None)):
    """获取提供商推荐"""
    try:
        recommendations = db_service.get_provider_recommendations(model_name)
        return {
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
                    "reason": rec["reason"]
                }
                for rec in recommendations
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商推荐失败: {str(e)}")


@providers_router.get("/{provider_name}/best-for-model")
async def get_best_provider_for_model(model_name: str):
    """为指定模型获取最佳提供商"""
    try:
        best_provider = db_service.get_best_provider_for_model(model_name)
        if not best_provider:
            raise HTTPException(status_code=404, detail=f"模型 {model_name} 没有可用的提供商")
        
        return {
            "model_name": model_name,
            "best_provider": {
                "id": best_provider.id,
                "name": best_provider.name,
                "provider_type": best_provider.provider_type,
                "official_endpoint": best_provider.official_endpoint,
                "third_party_endpoint": best_provider.third_party_endpoint,
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取最佳提供商失败: {str(e)}")


@providers_router.put("/{provider_name}/health")
async def update_provider_health(provider_name: str, health_status: str):
    """更新提供商的健康状态"""
    try:
        if health_status not in ["healthy", "degraded", "unhealthy"]:
            raise HTTPException(status_code=400, detail="健康状态必须是 healthy、degraded 或 unhealthy")
        
        success = db_service.update_provider_health_status(provider_name, health_status)
        if not success:
            raise HTTPException(status_code=404, detail=f"提供商 {provider_name} 不存在")
        
        return {"message": f"提供商 {provider_name} 的健康状态已更新为 {health_status}"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"更新提供商健康状态失败: {str(e)}")


@providers_router.get("/stats/overview")
async def get_providers_overview():
    """获取提供商概览统计"""
    try:
        providers_with_health = db_service.get_all_providers_with_health()
        
        total_providers = len(providers_with_health)
        healthy_providers = len([p for p in providers_with_health if p["health_info"]["overall_health"] == "healthy"])
        degraded_providers = len([p for p in providers_with_health if p["health_info"]["overall_health"] == "degraded"])
        unhealthy_providers = len([p for p in providers_with_health if p["health_info"]["overall_health"] == "unhealthy"])
        
        avg_score = sum(p["health_info"]["average_score"] for p in providers_with_health) / total_providers if total_providers > 0 else 0
        
        return {
            "total_providers": total_providers,
            "healthy_providers": healthy_providers,
            "degraded_providers": degraded_providers,
            "unhealthy_providers": unhealthy_providers,
            "average_score": avg_score,
            "health_distribution": {
                "healthy_percentage": (healthy_providers / total_providers * 100) if total_providers > 0 else 0,
                "degraded_percentage": (degraded_providers / total_providers * 100) if total_providers > 0 else 0,
                "unhealthy_percentage": (unhealthy_providers / total_providers * 100) if total_providers > 0 else 0,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商概览失败: {str(e)}")
