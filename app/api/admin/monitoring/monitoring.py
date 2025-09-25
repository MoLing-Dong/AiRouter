"""
监控管理模块
提供系统监控相关的API接口
"""

from fastapi import APIRouter
from typing import Dict, Any

# 创建监控路由
monitoring_router = APIRouter(tags=["Monitoring"])


@monitoring_router.get("/status")
async def get_monitoring_status() -> Dict[str, Any]:
    """
    获取系统监控状态
    """
    return {
        "status": "healthy",
        "message": "监控系统运行正常",
        "timestamp": "2025-09-25T21:30:00Z",
    }


@monitoring_router.get("/metrics")
async def get_system_metrics() -> Dict[str, Any]:
    """
    获取系统性能指标
    """
    return {
        "cpu_usage": 45.2,
        "memory_usage": 67.8,
        "disk_usage": 32.1,
        "active_connections": 12,
        "total_requests": 1456,
        "error_rate": 0.2,
    }
