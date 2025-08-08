from fastapi import APIRouter, HTTPException
from typing import Dict, Any
from app.services.adapter_pool import adapter_pool

pool_router = APIRouter(prefix="/v1/pool", tags=["适配器池管理"])


@pool_router.get("/stats")
async def get_pool_stats():
    """获取适配器池统计信息"""
    try:
        stats = adapter_pool.get_pool_stats()
        return {
            "success": True,
            "data": stats,
            "message": "获取适配器池统计信息成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取适配器池统计信息失败: {str(e)}")


@pool_router.post("/cleanup")
async def cleanup_pool():
    """手动清理适配器池"""
    try:
        await adapter_pool._cleanup_expired_adapters()
        return {
            "success": True,
            "message": "适配器池清理完成"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理适配器池失败: {str(e)}")


@pool_router.post("/health-check")
async def health_check_pool():
    """手动执行健康检查"""
    try:
        await adapter_pool._check_all_adapters_health()
        return {
            "success": True,
            "message": "适配器池健康检查完成"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"健康检查失败: {str(e)}")


@pool_router.get("/status")
async def get_pool_status():
    """获取适配器池状态"""
    try:
        stats = adapter_pool.get_pool_stats()
        
        # 计算总体状态
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
            "message": "获取适配器池状态成功"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取适配器池状态失败: {str(e)}")
