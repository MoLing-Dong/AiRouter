"""
SQLModel数据库表模型定义
只包含数据库表模型和相关的枚举、基类
"""

from sqlmodel import SQLModel, Field, Relationship, select
from sqlalchemy import Column, JSON, ForeignKey, Integer
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==================== 枚举类型 ====================


class HealthStatus(str, Enum):
    """健康状态枚举 - 匹配数据库中的实际值"""

    healthy = "healthy"
    degraded = "degraded"
    unhealthy = "unhealthy"
    # 保持大写别名以兼容旧代码
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


# 为了向后兼容，创建别名
HealthStatusEnum = HealthStatus


class LLMType(str, Enum):
    """LLM类型枚举 - 表示模型的访问类型"""

    PUBLIC = "PUBLIC"  # 公开模型
    PRIVATE = "PRIVATE"  # 私有模型
    # 向后兼容旧的枚举值
    CHAT = "PUBLIC"  # chat类型视为公开
    COMPLETION = "PUBLIC"  # completion类型视为公开
    EMBEDDING = "PUBLIC"  # embedding类型视为公开
    IMAGE = "PUBLIC"  # image类型视为公开


# 为了向后兼容，创建别名
LLMTypeEnum = LLMType


class ProviderType(str, Enum):
    """提供商类型枚举"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    VOLCENGINE = "volcengine"
    CUSTOM = "custom"
    # 向后兼容旧的枚举值
    PUBLIC_CLOUD = "PUBLIC_CLOUD"
    THIRD_PARTY = "THIRD_PARTY"
    PRIVATE = "PRIVATE"


# 为了向后兼容，创建别名
ProviderTypeEnum = ProviderType


# ==================== Mixin 类 ====================


class TimestampMixin(SQLModel):
    """时间戳混入类"""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ==================== 数据库表模型基类 ====================


class LLMModelBase(SQLModel):
    """LLM模型基础类 - 匹配现有数据库结构"""

    name: str = Field(max_length=100, unique=True, index=True)
    llm_type: LLMType = Field(
        default=LLMType.PUBLIC,
        description="模型访问类型：PUBLIC=公开模型，PRIVATE=私有模型",
    )
    description: Optional[str] = Field(default=None)
    is_enabled: bool = Field(default=True, index=True)


class LLMProviderBase(SQLModel):
    """LLM提供商基础类 - 匹配现有数据库结构"""

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    name: str = Field(max_length=100)
    provider_type: ProviderType = Field()
    official_endpoint: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    is_enabled: bool = Field(default=True)


class LLMModelProviderBase(SQLModel):
    """模型-提供商关联基础类"""

    llm_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("llm_models.id", ondelete="CASCADE"), index=True
        )
    )
    provider_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("llm_providers.id", ondelete="CASCADE"), index=True
        )
    )
    weight: int = Field(default=10, ge=1, le=100)
    priority: int = Field(default=0, ge=0, le=100)
    is_enabled: bool = Field(default=True, index=True)
    is_preferred: bool = Field(default=False, index=True)

    # 健康状态和性能指标
    health_status: HealthStatus = Field(default=HealthStatus.HEALTHY, index=True)
    response_time_avg: float = Field(default=0.0, ge=0.0)
    response_time_min: float = Field(default=0.0, ge=0.0)
    response_time_max: float = Field(default=0.0, ge=0.0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)

    # 请求统计
    total_requests: int = Field(default=0, ge=0)
    successful_requests: int = Field(default=0, ge=0)
    failed_requests: int = Field(default=0, ge=0)

    # 成本统计
    total_cost: float = Field(default=0.0, ge=0.0)
    total_tokens_used: int = Field(default=0, ge=0)
    cost_per_1k_tokens: float = Field(default=0.0, ge=0.0)

    # 评分系统
    health_score: float = Field(default=1.0, ge=0.0, le=1.0)
    performance_score: float = Field(default=1.0, ge=0.0, le=1.0)
    cost_score: float = Field(default=1.0, ge=0.0, le=1.0)
    overall_score: float = Field(default=1.0, ge=0.0, le=1.0, index=True)

    # 故障管理
    failure_count: int = Field(default=0, ge=0)
    max_failures: int = Field(default=5, ge=1)
    auto_disable_on_failure: bool = Field(default=True)
    last_failure_time: Optional[datetime] = Field(default=None)
    last_health_check: Optional[datetime] = Field(default=None)


class LLMProviderApiKeyBase(SQLModel):
    """API密钥基础类 - 匹配现有数据库结构"""

    provider_id: int = Field(foreign_key="llm_providers.id", index=True)
    name: Optional[str] = Field(default=None, max_length=100)
    api_key: str = Field()
    is_enabled: bool = Field(default=True)
    is_preferred: bool = Field(default=False)
    weight: int = Field(default=10)
    daily_quota: Optional[int] = Field(default=None)
    usage_count: int = Field(default=0)
    description: Optional[str] = Field(default=None)


class CapabilityBase(SQLModel):
    """能力基础类"""

    capability_name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None)


class LLMModelCapabilityBase(SQLModel):
    """模型-能力关联基础类"""

    model_id: int = Field(
        sa_column=Column(
            Integer, ForeignKey("llm_models.id", ondelete="CASCADE"), primary_key=True
        )
    )
    capability_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("capabilities.capability_id", ondelete="CASCADE"),
            primary_key=True,
        )
    )

    class Config:
        protected_namespaces = ()


# ==================== 数据库表模型 ====================


class LLMModel(LLMModelBase, TimestampMixin, table=True):
    """LLM模型表"""

    __tablename__ = "llm_models"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    # 关系定义 - 配置 ORM 级联删除
    providers: List["LLMModelProvider"] = Relationship(
        back_populates="model", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    capabilities: List["LLMModelCapability"] = Relationship(
        back_populates="llm_model",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class LLMProvider(LLMProviderBase, TimestampMixin, table=True):
    """LLM提供商表"""

    __tablename__ = "llm_providers"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)

    # 关系定义
    models: List["LLMModelProvider"] = Relationship(back_populates="provider")
    api_keys: List["LLMProviderApiKey"] = Relationship(back_populates="provider")


class LLMModelProvider(LLMModelProviderBase, TimestampMixin, table=True):
    """模型-提供商关联表"""

    __tablename__ = "llm_model_providers"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 关系定义
    model: LLMModel = Relationship(back_populates="providers")
    provider: LLMProvider = Relationship(back_populates="models")


class LLMProviderApiKey(LLMProviderApiKeyBase, TimestampMixin, table=True):
    """API密钥表"""

    __tablename__ = "llm_provider_apikeys"

    id: Optional[int] = Field(default=None, primary_key=True)

    # 关系定义
    provider: LLMProvider = Relationship(back_populates="api_keys")


class Capability(CapabilityBase, table=True):
    """能力表 - 匹配实际数据库结构（无时间戳字段）"""

    __tablename__ = "capabilities"

    capability_id: Optional[int] = Field(default=None, primary_key=True)

    # 关系定义
    llm_models: List["LLMModelCapability"] = Relationship(back_populates="capability")


class LLMModelCapability(LLMModelCapabilityBase, table=True):
    """模型-能力关联表（多对多关系）"""

    __tablename__ = "llm_model_capabilities"

    # 关系定义
    llm_model: LLMModel = Relationship(back_populates="capabilities")
    capability: Capability = Relationship(back_populates="llm_models")


# 更新LLMModel以包含capabilities关系
LLMModel.model_rebuild()
