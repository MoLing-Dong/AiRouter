import time
from fastapi import APIRouter, HTTPException
from app.services.router import router, LoadBalancingStrategy
from app.services import adapter_manager
from .dto import StrategyRequest, StatsResponse, StrategyResponse, RefreshResponse

stats_router = APIRouter(prefix="/v1/stats", tags=["统计管理"])


@stats_router.get("/", response_model=StatsResponse)
async def get_routing_stats():
    """获取路由统计信息"""
    try:
        stats = router.get_routing_stats()
        return StatsResponse(
            timestamp=time.time(),
            stats=stats,
            use_database=adapter_manager.use_database,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@stats_router.post("/strategy", response_model=StrategyResponse)
async def set_routing_strategy(request: StrategyRequest):
    """设置路由策略"""
    try:
        router.set_strategy(LoadBalancingStrategy(request.strategy))
        return StrategyResponse(
            message=f"路由策略已设置为: {request.strategy}",
            strategy=request.strategy,
        )
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"无效的路由策略: {request.strategy}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"设置路由策略失败: {str(e)}")


@stats_router.post("/stats/reset")
async def reset_stats():
    """重置路由统计"""
    try:
        router.reset_stats()
        return {"message": "统计信息已重置"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"重置统计失败: {str(e)}")


@stats_router.post("/refresh", response_model=RefreshResponse)
async def refresh_config():
    """从数据库刷新模型配置"""
    try:
        adapter_manager.refresh_from_database()
        return RefreshResponse(
            message="配置已从数据库刷新",
            models_count=len(adapter_manager.get_available_models()),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新配置失败: {str(e)}")
