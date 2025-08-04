import time
from fastapi import APIRouter, HTTPException
from app.services.router import router, LoadBalancingStrategy
from app.core.adapters import adapter_manager

stats_router = APIRouter(prefix="/v1", tags=["统计管理"])


@stats_router.get("/stats")
async def get_routing_stats():
    """获取路由统计信息"""
    try:
        stats = router.get_routing_stats()
        return {
            "timestamp": time.time(),
            "stats": stats,
            "use_database": adapter_manager.use_database,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@stats_router.post("/strategy")
async def set_routing_strategy(strategy: str):
    """设置路由策略"""
    try:
        router.set_strategy(LoadBalancingStrategy(strategy))
        return {"message": f"路由策略已设置为: {strategy}", "strategy": strategy}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"无效的路由策略: {strategy}")
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


@stats_router.post("/refresh")
async def refresh_config():
    """从数据库刷新模型配置"""
    try:
        adapter_manager.refresh_from_database()
        return {
            "message": "配置已从数据库刷新",
            "models_count": len(adapter_manager.get_available_models()),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新配置失败: {str(e)}")
