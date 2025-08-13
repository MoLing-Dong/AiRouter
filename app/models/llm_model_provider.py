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
    """Health status enum"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class LoadBalancingStrategyEnum(str, Enum):
    """Load balancing strategy enum"""
    AUTO = "auto"  # Auto select best provider
    SPECIFIED_PROVIDER = "specified_provider"  # Specify provider
    FALLBACK = "fallback"  # Fallback
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # Weighted round robin
    LEAST_CONNECTIONS = "least_connections"  # Least connections
    RESPONSE_TIME = "response_time"  # Response time priority
    COST_OPTIMIZED = "cost_optimized"  # Cost optimized
    HYBRID = "hybrid"  # Hybrid strategy


class LLMModelProvider(Base):
    """LLM model-provider association table"""

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
    
    # Load balancing strategy configuration
    load_balancing_strategy = Column(
        String(50), 
        default=LoadBalancingStrategyEnum.AUTO.value,
        nullable=False
    )  # Load balancing strategy
    strategy_config = Column(JSON, default=dict)  # Strategy configuration parameters
    priority = Column(Integer, default=0)  # Priority (number smaller is higher priority)
    
    # Strategy specific configuration
    max_retries = Column(Integer, default=3)  # Maximum retry count
    retry_delay = Column(Float, default=1.0)  # Retry delay (seconds)
    circuit_breaker_enabled = Column(Boolean, default=True)  # Whether to enable circuit breaker
    circuit_breaker_threshold = Column(Integer, default=5)  # Circuit breaker threshold
    circuit_breaker_timeout = Column(Integer, default=60)  # Circuit breaker timeout (seconds)
    
    # Health status related fields
    health_status = Column(String(20), default=HealthStatusEnum.HEALTHY.value)
    last_health_check = Column(DateTime(timezone=True))
    health_check_interval = Column(Integer, default=300)  # Health check interval (seconds)
    
    # Performance metrics fields
    response_time_avg = Column(Float, default=0.0)  # Average response time (seconds)
    response_time_min = Column(Float, default=0.0)  # Minimum response time
    response_time_max = Column(Float, default=0.0)  # Maximum response time
    success_rate = Column(Float, default=1.0)  # Success rate (0-1)
    total_requests = Column(BigInteger, default=0)  # Total requests
    successful_requests = Column(BigInteger, default=0)  # Successful requests
    failed_requests = Column(BigInteger, default=0)  # Failed requests
    
    # Cost related fields
    cost_per_1k_tokens = Column(Float, default=0.0)  # Cost per 1K tokens
    total_cost = Column(Float, default=0.0)  # Total cost
    total_tokens_used = Column(BigInteger, default=0)  # Total tokens used
    
    # Score and priority
    health_score = Column(Float, default=1.0)  # Health score (0-1)
    performance_score = Column(Float, default=1.0)  # Performance score
    cost_score = Column(Float, default=1.0)  # Cost score
    overall_score = Column(Float, default=1.0)  # Overall score
    
    # Failure transfer and degradation configuration
    max_failures = Column(Integer, default=3)  # Maximum failure count
    failure_count = Column(Integer, default=0)  # Current failure count
    last_failure_time = Column(DateTime(timezone=True))  # Last failure time
    auto_disable_on_failure = Column(Boolean, default=True)  # Auto disable on failure
    
    # Monitoring and alerting
    alert_threshold = Column(Float, default=0.8)  # Alert threshold
    is_alerting = Column(Boolean, default=False)  # Whether in alert state
    last_alert_time = Column(DateTime(timezone=True))  # Last alert time
    
    # Extended configuration
    custom_config = Column(JSON)  # Custom configuration
    model_metadata = Column(JSON)  # Model metadata
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
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
