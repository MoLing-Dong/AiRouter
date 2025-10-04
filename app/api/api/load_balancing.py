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


@router.get(
    "/model/{model_id}/strategies", response_model=ApiResponse[List[StrategyInfo]]
)
async def get_model_strategies(
    model_id: int = Path(..., gt=0, description="模型ID", example=1, title="Model ID")
) -> ApiResponse[List[StrategyInfo]]:
    """Get all provider strategies for specified model"""
    strategies = db_service.get_model_strategies(model_id)
    if not strategies:
        raise HTTPException(
            status_code=404, detail=f"Model {model_id} has no strategy configuration"
        )

    strategy_list = [StrategyInfo(**strategy) for strategy in strategies]
    return ApiResponse.success(data=strategy_list, message="获取模型策略成功")


@router.get(
    "/model/{model_name}/provider/{provider_name}/strategy",
    response_model=ApiResponse[dict],
)
async def get_model_provider_strategy(
    model_name: str, provider_name: str
) -> ApiResponse[dict]:
    """Get model-provider load balancing strategy"""
    strategy = db_service.get_model_provider_strategy(model_name, provider_name)
    if not strategy:
        raise HTTPException(
            status_code=404,
            detail=f"Model {model_name} and provider {provider_name} strategy configuration not found",
        )

    return ApiResponse.success(data=strategy, message="获取策略配置成功")


@router.put(
    "/model/{model_name}/provider/{provider_name}/strategy",
    response_model=ApiResponse[None],
)
async def update_model_provider_strategy(
    model_name: str, provider_name: str, request: StrategyUpdateRequest
) -> ApiResponse[None]:
    """Update model-provider load balancing strategy"""
    # Validate strategy is valid
    if request.strategy not in db_service.get_available_strategies():
        raise HTTPException(
            status_code=400,
            detail=f"Invalid load balancing strategy: {request.strategy}",
        )

    success = db_service.update_model_provider_strategy(
        model_name,
        provider_name,
        request.strategy,
        request.strategy_config,
        request.priority,
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Update strategy failed, please check if model {model_name} and provider {provider_name} exist",
        )

    return ApiResponse.success(message="Strategy updated successfully")


@router.put(
    "/model/{model_name}/provider/{provider_name}/circuit-breaker",
    response_model=ApiResponse[None],
)
async def update_model_provider_circuit_breaker(
    model_name: str, provider_name: str, request: CircuitBreakerUpdateRequest
) -> ApiResponse[None]:
    """Update model-provider circuit breaker configuration"""
    success = db_service.update_model_provider_circuit_breaker(
        model_name, provider_name, request.enabled, request.threshold, request.timeout
    )

    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Update circuit breaker configuration failed, please check if model {model_name} and provider {provider_name} exist",
        )

    return ApiResponse.success(
        message="Circuit breaker configuration updated successfully"
    )


@router.get("/statistics", response_model=ApiResponse[dict])
async def get_strategy_statistics(
    model_name: Optional[str] = Query(
        None,
        min_length=1,
        max_length=100,
        description="模型名称，如果提供则不能为空字符串",
    )
) -> ApiResponse[dict]:
    """Get strategy usage statistics"""
    stats = db_service.get_strategy_statistics(model_name)
    return ApiResponse.success(data=stats, message="获取策略统计成功")


@router.get("/model/{model_name}/recommendations", response_model=ApiResponse[dict])
async def get_strategy_recommendations(model_name: str) -> ApiResponse[dict]:
    """Get best strategy recommendations for model"""
    try:
        from app.services.load_balancing.router import SmartRouter

        smart_router = SmartRouter()
        recommendations = smart_router.get_routing_recommendations(model_name)

        if "error" in recommendations:
            raise HTTPException(status_code=404, detail=recommendations["error"])

        return ApiResponse.success(data=recommendations, message="获取策略推荐成功")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get strategy recommendations failed: {str(e)}"
        )


@router.post("/model/{model_name}/test-strategy", response_model=ApiResponse[dict])
async def test_strategy(
    model_name: str, strategy: str, strategy_config: Optional[Dict[str, Any]] = None
) -> ApiResponse[dict]:
    """Test load balancing strategy"""
    try:
        from app.services.load_balancing.load_balancing_strategies import (
            strategy_manager,
        )
        from app.core.adapters import ChatRequest, Message, MessageRole

        # Create test request
        test_request = ChatRequest(
            model=model_name,
            messages=[Message(role=MessageRole.USER, content="Test message")],
            max_tokens=10,
            temperature=0.7,
        )

        # Get all providers for the model
        model_providers = db_service.get_model_providers(
            db_service.get_model_by_name(model_name).id, is_enabled=True
        )

        if not model_providers:
            raise HTTPException(
                status_code=404, detail=f"Model {model_name} has no available provider"
            )

        # Execute strategy test
        response = await strategy_manager.execute_strategy(
            test_request, model_providers, strategy, strategy_config
        )

        result_data = {
            "selected_provider": "Test completed",
            "response_preview": (
                response.content[:100] + "..."
                if len(response.content) > 100
                else response.content
            ),
        }

        return ApiResponse.success(data=result_data, message="Strategy test successful")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy test failed: {str(e)}")


@router.get("/info", response_model=ApiResponse[dict])
async def get_load_balancing_info() -> ApiResponse[dict]:
    """Get load balancing system information"""
    try:
        from app.services.load_balancing.load_balancing_strategies import (
            strategy_manager,
        )

        info = {
            "available_strategies": db_service.get_available_strategies(),
            "strategy_manager_info": strategy_manager.get_strategy_info(),
            "system_statistics": db_service.get_strategy_statistics(),
        }
        return ApiResponse.success(data=info, message="获取负载均衡系统信息成功")
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Get system information failed: {str(e)}"
        )
