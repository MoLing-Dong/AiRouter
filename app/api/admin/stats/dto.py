from pydantic import BaseModel


class StatsResponse(BaseModel):
    """Statistics information response DTO"""
    timestamp: float
    stats: dict
    use_database: bool


class RefreshResponse(BaseModel):
    """Configuration refresh response DTO"""
    message: str
    models_count: int 