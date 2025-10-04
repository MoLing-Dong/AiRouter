from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.adapters.adapter_pool import AdapterPool
from app.models import ApiResponse
from app.utils.logging_config import get_factory_logger

# Initialize adapter pool
adapter_pool = AdapterPool()

# Get logger
logger = get_factory_logger()

pool_router = APIRouter(tags=["Adapter Pool Management"])


@pool_router.get("/stats", response_model=ApiResponse[dict])
async def get_pool_stats() -> ApiResponse[dict]:
    """Get adapter pool statistics information"""
    try:
        stats = adapter_pool.get_pool_stats()
        return ApiResponse.success(
            data=stats,
            message="Get adapter pool statistics information successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Get adapter pool statistics information failed: {str(e)}",
        )


@pool_router.post("/cleanup", response_model=ApiResponse[None])
async def cleanup_pool() -> ApiResponse[None]:
    """Manual cleanup adapter pool"""
    try:
        await adapter_pool._cleanup_expired_adapters()
        return ApiResponse.success(message="Adapter pool cleanup completed")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Cleanup adapter pool failed: {str(e)}"
        )


@pool_router.post("/health-check", response_model=ApiResponse[None])
async def health_check_pool() -> ApiResponse[None]:
    """Manual health check"""
    try:
        await adapter_pool._check_all_adapters_health()
        return ApiResponse.success(message="Adapter pool health check completed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@pool_router.get("/status", response_model=ApiResponse[dict])
async def get_pool_status() -> ApiResponse[dict]:
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
            "utilization_rate": (
                (in_use_adapters / total_adapters * 100) if total_adapters > 0 else 0
            ),
            "health_rate": (
                ((total_adapters - unhealthy_adapters) / total_adapters * 100)
                if total_adapters > 0
                else 0
            ),
        }

        return ApiResponse.success(
            data=status,
            message="Get adapter pool status successfully",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get adapter pool status failed: {str(e)}"
        )
