from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.adapters.adapter_pool import AdapterPool

# Initialize adapter pool
adapter_pool = AdapterPool()
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()

pool_router = APIRouter(prefix="/v1/pool", tags=["Adapter Pool Management"])


@pool_router.get("/stats")
async def get_pool_stats():
    """Get adapter pool statistics information"""
    try:
        stats = adapter_pool.get_pool_stats()
        return {
            "success": True,
            "data": stats,
            "message": "Get adapter pool statistics information successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get adapter pool statistics information failed: {str(e)}")


@pool_router.post("/cleanup")
async def cleanup_pool():
    """Manual cleanup adapter pool"""
    try:
        await adapter_pool._cleanup_expired_adapters()
        return {
            "success": True,
            "message": "Adapter pool cleanup completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cleanup adapter pool failed: {str(e)}")


@pool_router.post("/health-check")
async def health_check_pool():
    """Manual health check"""
    try:
        await adapter_pool._check_all_adapters_health()
        return {
            "success": True,
            "message": "Adapter pool health check completed"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@pool_router.get("/status")
async def get_pool_status():
    """Get adapter pool status"""
    try:
        stats = adapter_pool.get_pool_stats()
        
        # Calculate overall status
        total_adapters = sum(pool["total"] for pool in stats["pools"].values())
        available_adapters = sum(pool["available"] for pool in stats["pools"].values())
        in_use_adapters = sum(pool["in_use"] for pool in stats["pools"].values())
        unhealthy_adapters = sum(pool["unhealthy"] for pool in stats["pools"].values())
        
        status = {
            "total_pools": stats["total_pools"],
            "total_adapters": total_adapters,
            "available_adapters": available_adapters,
            "in_use_adapters": in_use_adapters,
            "unhealthy_adapters": unhealthy_adapters,
            "utilization_rate": (in_use_adapters / total_adapters * 100) if total_adapters > 0 else 0,
            "health_rate": ((total_adapters - unhealthy_adapters) / total_adapters * 100) if total_adapters > 0 else 0
        }
        
        return {
            "success": True,
            "data": status,
            "message": "Get adapter pool status successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get adapter pool status failed: {str(e)}")
