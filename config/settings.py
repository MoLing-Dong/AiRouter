from pydantic_settings import BaseSettings
from typing import Dict, List, Optional, Any
import os


class ModelProvider(BaseSettings):
    """模型提供商配置"""

    name: str
    base_url: str
    api_key: str
    weight: float = 1.0
    max_tokens: int = 4096
    temperature: float = 0.7
    cost_per_1k_tokens: float = 0.0
    timeout: int = 30
    retry_count: int = 3
    enabled: bool = True


class ModelConfig(BaseSettings):
    """模型配置"""

    name: str
    providers: List[ModelProvider]
    model_type: str = "chat"
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    enabled: bool = True
    priority: int = 0

    class Config:
        protected_namespaces = ()


class LoadBalancingConfig(BaseSettings):
    """负载均衡配置"""

    strategy: str = "auto"  # 更新为新的策略：auto, specified_provider, fallback
    health_check_interval: int = 30
    max_retries: int = 3
    timeout: int = 30
    enable_fallback: bool = True
    enable_cost_optimization: bool = True

    class Config:
        env_prefix = "LOAD_BALANCING_"
        case_sensitive = False


class MonitoringConfig(BaseSettings):
    """监控配置"""

    enabled: bool = True
    metrics_interval: int = 60
    log_level: str = "INFO"
    enable_performance_tracking: bool = True
    enable_cost_tracking: bool = True


class SecurityConfig(BaseSettings):
    """安全配置"""

    rate_limit: int = 100
    api_key_required: bool = True
    cors_origins: List[str] = ["*"]
    enable_request_logging: bool = True


class Settings(BaseSettings):
    # 应用基础配置
    APP_NAME: str = "AI路由器"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    RUN_ENV: str = "dev"
    LOG_LEVEL: str = "INFO"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Redis配置
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0

    # 数据库配置
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/database"

    # 数据库连接池配置
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600

    # 负载均衡配置
    LOAD_BALANCING: LoadBalancingConfig = LoadBalancingConfig()

    # 监控配置
    MONITORING: MonitoringConfig = MonitoringConfig()

    # 安全配置
    SECURITY: SecurityConfig = SecurityConfig()

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 忽略额外的环境变量


settings = Settings()
