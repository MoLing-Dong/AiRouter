from pydantic import BaseModel


class StrategyRequest(BaseModel):
    """路由策略请求DTO"""
    strategy: str


class StatsResponse(BaseModel):
    """统计信息响应DTO"""
    timestamp: float
    stats: dict
    use_database: bool


class StrategyResponse(BaseModel):
    """策略设置响应DTO"""
    message: str
    strategy: str


class RefreshResponse(BaseModel):
    """配置刷新响应DTO"""
    message: str
    models_count: int 