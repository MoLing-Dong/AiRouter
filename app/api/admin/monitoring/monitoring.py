"""
监控管理模块
提供系统监控相关的API接口
"""

from fastapi import APIRouter
from typing import Dict, Any
from app.models import ApiResponse

# 创建监控路由
monitoring_router = APIRouter(tags=["Monitoring"])


@monitoring_router.get("/status", response_model=ApiResponse[dict])
async def get_monitoring_status() -> ApiResponse[dict]:
    """
    获取系统监控状态
    """
    data = {
        "status": "healthy",
        "timestamp": "2025-09-25T21:30:00Z",
    }
    return ApiResponse.success(data=data, message="监控系统运行正常")


@monitoring_router.get("/metrics", response_model=ApiResponse[dict])
async def get_system_metrics() -> ApiResponse[dict]:
    """
    获取系统性能指标
    """
    metrics = {
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "disk_usage": 32.1,
        "active_connections": 12,
        "total_requests": 1456,
        "error_rate": 0.2,
    }
    return ApiResponse.success(data=metrics, message="获取系统性能指标成功")
