"""
负载均衡策略管理API
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from ...services.database_service import db_service
from ...services.load_balancing_strategies import LoadBalancingStrategy

router = APIRouter(prefix="/v1/load-balancing", tags=["负载均衡策略"])


class StrategyUpdateRequest(BaseModel):
    """策略更新请求"""
    strategy: str
    strategy_config: Optional[Dict[str, Any]] = None
    priority: Optional[int] = None


class CircuitBreakerUpdateRequest(BaseModel):
    """熔断器更新请求"""
    enabled: Optional[bool] = None
    threshold: Optional[int] = None
    timeout: Optional[int] = None


class StrategyInfo(BaseModel):
    """策略信息"""
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
    """获取所有可用的负载均衡策略"""
    return db_service.get_available_strategies()


@router.get("/model/{model_name}/strategies", response_model=List[StrategyInfo])
async def get_model_strategies(model_name: str):
    """获取指定模型的所有供应商策略"""
    strategies = db_service.get_model_strategies(model_name)
    if not strategies:
        raise HTTPException(status_code=404, detail=f"模型 {model_name} 没有找到策略配置")
    
    return [StrategyInfo(**strategy) for strategy in strategies]


@router.get("/model/{model_name}/provider/{provider_name}/strategy")
async def get_model_provider_strategy(model_name: str, provider_name: str):
    """获取模型-供应商的负载均衡策略"""
    strategy = db_service.get_model_provider_strategy(model_name, provider_name)
    if not strategy:
        raise HTTPException(
            status_code=404, 
            detail=f"模型 {model_name} 和供应商 {provider_name} 的策略配置未找到"
        )
    
    return strategy


@router.put("/model/{model_name}/provider/{provider_name}/strategy")
async def update_model_provider_strategy(
    model_name: str, 
    provider_name: str, 
    request: StrategyUpdateRequest
):
    """更新模型-供应商的负载均衡策略"""
    # 验证策略是否有效
    if request.strategy not in db_service.get_available_strategies():
        raise HTTPException(
            status_code=400, 
            detail=f"无效的负载均衡策略: {request.strategy}"
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
            detail=f"更新策略失败，请检查模型 {model_name} 和供应商 {provider_name} 是否存在"
        )
    
    return {"message": "策略更新成功"}


@router.put("/model/{model_name}/provider/{provider_name}/circuit-breaker")
async def update_model_provider_circuit_breaker(
    model_name: str, 
    provider_name: str, 
    request: CircuitBreakerUpdateRequest
):
    """更新模型-供应商的熔断器配置"""
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
            detail=f"更新熔断器配置失败，请检查模型 {model_name} 和供应商 {provider_name} 是否存在"
        )
    
    return {"message": "熔断器配置更新成功"}


@router.get("/statistics")
async def get_strategy_statistics(model_name: Optional[str] = None):
    """获取策略使用统计"""
    return db_service.get_strategy_statistics(model_name)


@router.get("/model/{model_name}/recommendations")
async def get_strategy_recommendations(model_name: str):
    """获取模型的最佳策略建议"""
    try:
        from ...services.router import router as smart_router
        recommendations = smart_router.get_routing_recommendations(model_name)
        
        if "error" in recommendations:
            raise HTTPException(status_code=404, detail=recommendations["error"])
        
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取策略建议失败: {str(e)}")


@router.post("/model/{model_name}/test-strategy")
async def test_strategy(
    model_name: str, 
    strategy: str, 
    strategy_config: Optional[Dict[str, Any]] = None
):
    """测试负载均衡策略"""
    try:
        from ...services.load_balancing_strategies import strategy_manager
        from ...core.adapters import ChatRequest, Message, MessageRole
        
        # 创建测试请求
        test_request = ChatRequest(
            model=model_name,
            messages=[Message(role=MessageRole.USER, content="测试消息")],
            max_tokens=10,
            temperature=0.7
        )
        
        # 获取模型的所有供应商
        model_providers = db_service.get_model_providers(
            db_service.get_model_by_name(model_name).id, 
            is_enabled=True
        )
        
        if not model_providers:
            raise HTTPException(
                status_code=404, 
                detail=f"模型 {model_name} 没有可用的供应商"
            )
        
        # 执行策略测试
        response = await strategy_manager.execute_strategy(
            test_request, model_providers, strategy, strategy_config
        )
        
        return {
            "message": "策略测试成功",
            "selected_provider": "测试完成",
            "response_preview": response.content[:100] + "..." if len(response.content) > 100 else response.content
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"策略测试失败: {str(e)}")


@router.get("/info")
async def get_load_balancing_info():
    """获取负载均衡系统信息"""
    try:
        from ...services.load_balancing_strategies import strategy_manager
        
        return {
            "available_strategies": db_service.get_available_strategies(),
            "strategy_manager_info": strategy_manager.get_strategy_info(),
            "system_statistics": db_service.get_strategy_statistics(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取系统信息失败: {str(e)}")
