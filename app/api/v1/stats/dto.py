from pydantic import BaseModel


class StatsResponse(BaseModel):
    """统计信息响应DTO"""
    timestamp: float
    stats: dict
    use_database: bool


class RefreshResponse(BaseModel):
    """配置刷新响应DTO"""
    message: str
    models_count: int 