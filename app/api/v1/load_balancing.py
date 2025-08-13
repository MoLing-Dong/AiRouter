from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from app.services.database_service import db_service
from app.services.load_balancing_strategies import LoadBalancingStrategy

router = APIRouter(prefix="/v1/load-balancing", tags=["Load Balancing Strategy"])


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


@router.get("/strategies", response_model=List[str])
async def get_available_strategies():
    """Get all available load balancing strategies"""
    return db_service.get_available_strategies()


@router.get("/model/{model_name}/strategies", response_model=List[StrategyInfo])
async def get_model_strategies(model_name: str):
    """Get all provider strategies for specified model"""
    strategies = db_service.get_model_strategies(model_name)
    if not strategies:
        raise HTTPException(status_code=404, detail=f"Model {model_name} has no strategy configuration")
    
    return [StrategyInfo(**strategy) for strategy in strategies]


@router.get("/model/{model_name}/provider/{provider_name}/strategy")
async def get_model_provider_strategy(model_name: str, provider_name: str):
    """Get model-provider load balancing strategy"""
    strategy = db_service.get_model_provider_strategy(model_name, provider_name)
    if not strategy:
        raise HTTPException(
            status_code=404, 
            detail=f"Model {model_name} and provider {provider_name} strategy configuration not found"
        )
    
    return strategy


@router.put("/model/{model_name}/provider/{provider_name}/strategy")
async def update_model_provider_strategy(
    model_name: str, 
    provider_name: str, 
    request: StrategyUpdateRequest
):
    """Update model-provider load balancing strategy"""
    # Validate strategy is valid
    if request.strategy not in db_service.get_available_strategies():
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid load balancing strategy: {request.strategy}"
        )
    
    success = db_service.update_model_provider_strategy(
        model_name, 
        provider_name, 
        request.strategy,
        request.strategy_config,
        request.priority
    )
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail=f"Update strategy failed, please check if model {model_name} and provider {provider_name} exist"
        )
    
    return {"message": "Strategy updated successfully"}


@router.put("/model/{model_name}/provider/{provider_name}/circuit-breaker")
async def update_model_provider_circuit_breaker(
    model_name: str, 
    provider_name: str, 
    request: CircuitBreakerUpdateRequest
):
    """Update model-provider circuit breaker configuration"""
    success = db_service.update_model_provider_circuit_breaker(
        model_name, 
        provider_name,
        request.enabled,
        request.threshold,
        request.timeout
    )
    
    if not success:
        raise HTTPException(
            status_code=404, 
            detail=f"Update circuit breaker configuration failed, please check if model {model_name} and provider {provider_name} exist"
        )
    
    return {"message": "Circuit breaker configuration updated successfully"}


@router.get("/statistics")
async def get_strategy_statistics(model_name: Optional[str] = None):
    """Get strategy usage statistics"""
    return db_service.get_strategy_statistics(model_name)


@router.get("/model/{model_name}/recommendations")
async def get_strategy_recommendations(model_name: str):
    """Get best strategy recommendations for model"""
    try:
        from app.services.router import router as smart_router
        recommendations = smart_router.get_routing_recommendations(model_name)
        
        if "error" in recommendations:
            raise HTTPException(status_code=404, detail=recommendations["error"])
        
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get strategy recommendations failed: {str(e)}")


@router.post("/model/{model_name}/test-strategy")
async def test_strategy(
    model_name: str, 
    strategy: str, 
    strategy_config: Optional[Dict[str, Any]] = None
):
    """Test load balancing strategy"""
    try:
        from app.services.load_balancing_strategies import strategy_manager
        from app.core.adapters import ChatRequest, Message, MessageRole
        
        # Create test request
        test_request = ChatRequest(
            model=model_name,
            messages=[Message(role=MessageRole.USER, content="Test message")],
            max_tokens=10,
            temperature=0.7
        )
        
        # Get all providers for the model
        model_providers = db_service.get_model_providers(
            db_service.get_model_by_name(model_name).id, 
            is_enabled=True
        )
        
        if not model_providers:
            raise HTTPException(
                status_code=404, 
                detail=f"Model {model_name} has no available provider"
            )
        
        # Execute strategy test
        response = await strategy_manager.execute_strategy(
            test_request, model_providers, strategy, strategy_config
        )
        
        return {
            "message": "Strategy test successful",
            "selected_provider": "Test completed",
            "response_preview": response.content[:100] + "..." if len(response.content) > 100 else response.content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Strategy test failed: {str(e)}")


@router.get("/info")
async def get_load_balancing_info():
    """Get load balancing system information"""
    try:
        from app.services.load_balancing_strategies import strategy_manager
        
        return {
            "available_strategies": db_service.get_available_strategies(),
            "strategy_manager_info": strategy_manager.get_strategy_info(),
            "system_statistics": db_service.get_strategy_statistics(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Get system information failed: {str(e)}")
