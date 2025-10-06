from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from app.services.database.database_service import db_service
from app.services.load_balancing.load_balancing_strategies import LoadBalancingStrategy
from app.models import ApiResponse

router = APIRouter(tags=["Load Balancing Strategy"])


class StrategyUpdateRequest(BaseModel):
    """Strategy update request"""

    strategy: str
    strategy_config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None


class CircuitBreakerUpdateRequest(BaseModel):
    """Circuit breaker update request"""

    enabled: Optional[bool] = None
    threshold: Optional[int] = None
    timeout: Optional[int] = None


class StrategyInfo(BaseModel):
    """Strategy information"""

    provider_name: str
    strategy: str
    strategy_config: Optional[Dict[str, Any]] = None
    priority: int
    weight: int
    is_preferred: bool
    health_status: str
    overall_score: float


@router.get("/strategies", response_model=ApiResponse[List[str]])
async def get_available_strategies() -> ApiResponse[List[str]]:
    """Get all available load balancing strategies"""
    strategies = db_service.get_available_strategies()
    return ApiResponse.success(data=strategies, message="获取负载均衡策略列表成功")

