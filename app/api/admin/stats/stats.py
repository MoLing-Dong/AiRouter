import time
from fastapi import APIRouter, HTTPException
from app.services.load_balancing.router import SmartRouter

# Initialize router
router = SmartRouter()
from app.services import adapter_manager
from .dto import StatsResponse, RefreshResponse

stats_router = APIRouter(tags=["Stats Management"])


@stats_router.get("/", response_model=StatsResponse)
async def get_routing_stats():
    """Get routing statistics information"""
    try:
        stats = router.get_routing_stats()
        return StatsResponse(
            timestamp=time.time(),
            stats=stats,
            use_database=adapter_manager.use_database,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get statistics information failed: {str(e)}"
        )


@stats_router.post("/reset")
async def reset_stats():
    """Reset routing statistics"""
    try:
        router.reset_stats()
        return {"message": "Statistics information has been reset"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Reset statistics failed: {str(e)}"
        )


@stats_router.post("/refresh", response_model=RefreshResponse)
async def refresh_config():
    """Refresh model configuration from database"""
    try:
        adapter_manager.refresh_from_database()
        return RefreshResponse(
            message="Configuration has been refreshed from database",
            models_count=len(adapter_manager.get_available_models()),
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Refresh configuration failed: {str(e)}"
        )
