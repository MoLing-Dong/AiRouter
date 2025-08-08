from sqlalchemy import (
    Column,
    BigInteger,
    Boolean,
    DateTime,
    Integer,
    ForeignKey,
    UniqueConstraint,
    CheckConstraint,
    Index,
    String,
    Float,
    Text,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from enum import Enum

from .base import Base


class HealthStatusEnum(str, Enum):
    """健康状态枚举"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class LoadBalancingStrategyEnum(str, Enum):
    """负载均衡策略枚举"""
    AUTO = "auto"  # 自动选择最佳供应商
    SPECIFIED_PROVIDER = "specified_provider"  # 指定供应商
    FALLBACK = "fallback"  # 故障转移
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # 加权轮询
    LEAST_CONNECTIONS = "least_connections"  # 最少连接数
    RESPONSE_TIME = "response_time"  # 响应时间优先
    COST_OPTIMIZED = "cost_optimized"  # 成本优化
    HYBRID = "hybrid"  # 混合策略


class LLMModelProvider(Base):
    """LLM模型-提供商关联表"""

    __tablename__ = "llm_model_providers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    llm_id = Column(
        BigInteger, ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False
    )
    provider_id = Column(
        BigInteger,
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    weight = Column(Integer, default=10)
    is_preferred = Column(Boolean, default=False)
    is_enabled = Column(Boolean, default=True)
    
    # 负载均衡策略配置
    load_balancing_strategy = Column(
        String(50), 
        default=LoadBalancingStrategyEnum.AUTO.value,
        nullable=False
    )  # 负载均衡策略
    strategy_config = Column(JSON, default=dict)  # 策略配置参数
    priority = Column(Integer, default=0)  # 优先级（数字越小优先级越高）
    
    # 策略特定配置
    max_retries = Column(Integer, default=3)  # 最大重试次数
    retry_delay = Column(Float, default=1.0)  # 重试延迟（秒）
    circuit_breaker_enabled = Column(Boolean, default=True)  # 是否启用熔断器
    circuit_breaker_threshold = Column(Integer, default=5)  # 熔断器阈值
    circuit_breaker_timeout = Column(Integer, default=60)  # 熔断器超时时间（秒）
    
    # 健康状态相关字段
    health_status = Column(String(20), default=HealthStatusEnum.HEALTHY.value)
    last_health_check = Column(DateTime(timezone=True))
    health_check_interval = Column(Integer, default=300)  # 健康检查间隔（秒）
    
    # 性能指标字段
    response_time_avg = Column(Float, default=0.0)  # 平均响应时间（秒）
    response_time_min = Column(Float, default=0.0)  # 最小响应时间
    response_time_max = Column(Float, default=0.0)  # 最大响应时间
    success_rate = Column(Float, default=1.0)  # 成功率（0-1）
    total_requests = Column(BigInteger, default=0)  # 总请求数
    successful_requests = Column(BigInteger, default=0)  # 成功请求数
    failed_requests = Column(BigInteger, default=0)  # 失败请求数
    
    # 成本相关字段
    cost_per_1k_tokens = Column(Float, default=0.0)  # 每1K tokens的成本
    total_cost = Column(Float, default=0.0)  # 总成本
    total_tokens_used = Column(BigInteger, default=0)  # 总使用的tokens
    
    # 评分和优先级
    health_score = Column(Float, default=1.0)  # 健康评分（0-1）
    performance_score = Column(Float, default=1.0)  # 性能评分
    cost_score = Column(Float, default=1.0)  # 成本评分
    overall_score = Column(Float, default=1.0)  # 综合评分
    
    # 故障转移和降级配置
    max_failures = Column(Integer, default=3)  # 最大失败次数
    failure_count = Column(Integer, default=0)  # 当前失败次数
    last_failure_time = Column(DateTime(timezone=True))  # 最后失败时间
    auto_disable_on_failure = Column(Boolean, default=True)  # 失败时自动禁用
    
    # 监控和告警
    alert_threshold = Column(Float, default=0.8)  # 告警阈值
    is_alerting = Column(Boolean, default=False)  # 是否处于告警状态
    last_alert_time = Column(DateTime(timezone=True))  # 最后告警时间
    
    # 扩展配置
    custom_config = Column(JSON)  # 自定义配置
    model_metadata = Column(JSON)  # 元数据
    
    # 时间戳
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # 关系
    llm_model = relationship("LLMModel", back_populates="providers")
    provider = relationship("LLMProvider", back_populates="models")

    __table_args__ = (
        UniqueConstraint(
            "llm_id", "provider_id", name="model_provider_llm_id_provider_id_key"
        ),
        CheckConstraint("weight > 0", name="model_provider_weight_check"),
        CheckConstraint("success_rate >= 0 AND success_rate <= 1", name="model_provider_success_rate_check"),
        CheckConstraint("health_score >= 0 AND health_score <= 1", name="model_provider_health_score_check"),
        CheckConstraint("performance_score >= 0 AND performance_score <= 1", name="model_provider_performance_score_check"),
        CheckConstraint("cost_score >= 0 AND cost_score <= 1", name="model_provider_cost_score_check"),
        CheckConstraint("overall_score >= 0 AND overall_score <= 1", name="model_provider_overall_score_check"),
        Index("idx_model_provider_llm", "llm_id"),
        Index("idx_model_provider_enabled_weight", "llm_id", "is_enabled", "weight"),
        Index("idx_model_provider_health", "llm_id", "health_status", "overall_score"),
        Index("idx_model_provider_performance", "llm_id", "response_time_avg", "success_rate"),
        Index("idx_model_provider_cost", "llm_id", "cost_per_1k_tokens"),
        Index("idx_model_provider_strategy", "llm_id", "load_balancing_strategy", "priority"),
    )
