"""
SQLModel模型定义 - 现代化的ORM模型
结合了Pydantic和SQLAlchemy的优势，提供更好的类型安全和性能
"""

from sqlmodel import SQLModel, Field, Relationship, select
from sqlalchemy import Column, JSON
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


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
    """LLM类型枚举"""
    CHAT = "chat"
    COMPLETION = "completion"
    EMBEDDING = "embedding"
    IMAGE = "image"
    # 向后兼容旧的枚举值
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"

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


# ==================== Base Models ====================

class TimestampMixin(SQLModel):
    """时间戳混入类"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class LLMModelBase(SQLModel):
    """LLM模型基础类 - 匹配现有数据库结构"""
    name: str = Field(max_length=100, unique=True, index=True)
    llm_type: LLMType = Field(default=LLMType.CHAT)
    description: Optional[str] = Field(default=None)
    is_enabled: bool = Field(default=True, index=True)


class LLMModel(LLMModelBase, TimestampMixin, table=True):
    """LLM模型表"""
    __tablename__ = "llm_models"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    
    # 关系定义
    providers: List["LLMModelProvider"] = Relationship(back_populates="model")
    parameters: List["LLMModelParam"] = Relationship(back_populates="model")
    capabilities: List["LLMModelCapability"] = Relationship(back_populates="llm_model")


class LLMProviderBase(SQLModel):
    """LLM提供商基础类 - 匹配现有数据库结构"""
    name: str = Field(max_length=100)
    provider_type: ProviderType = Field()
    official_endpoint: Optional[str] = Field(default=None, max_length=255)
    third_party_endpoint: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    is_enabled: bool = Field(default=True)


class LLMProvider(LLMProviderBase, TimestampMixin, table=True):
    """LLM提供商表"""
    __tablename__ = "llm_providers"
    
    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    
    # 关系定义
    models: List["LLMModelProvider"] = Relationship(back_populates="provider")
    api_keys: List["LLMProviderApiKey"] = Relationship(back_populates="provider")


class LLMModelProviderBase(SQLModel):
    """模型-提供商关联基础类"""
    llm_id: int = Field(foreign_key="llm_models.id", index=True)
    provider_id: int = Field(foreign_key="llm_providers.id", index=True)
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


class LLMModelProvider(LLMModelProviderBase, TimestampMixin, table=True):
    """模型-提供商关联表"""
    __tablename__ = "llm_model_providers"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 关系定义
    model: LLMModel = Relationship(back_populates="providers")
    provider: LLMProvider = Relationship(back_populates="models")


class LLMModelParamBase(SQLModel):
    """模型参数基础类"""
    llm_id: int = Field(foreign_key="llm_models.id", index=True)
    provider_id: Optional[int] = Field(default=None, foreign_key="llm_providers.id")
    param_key: str = Field(max_length=100, index=True)
    param_value: Any = Field(sa_column=Column(JSON))
    is_enabled: bool = Field(default=True, index=True)
    description: Optional[str] = Field(default=None, max_length=500)


class LLMModelParam(LLMModelParamBase, TimestampMixin, table=True):
    """模型参数表"""
    __tablename__ = "llm_model_params"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 关系定义
    model: LLMModel = Relationship(back_populates="parameters")


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


class LLMProviderApiKey(LLMProviderApiKeyBase, TimestampMixin, table=True):
    """API密钥表"""
    __tablename__ = "llm_provider_apikeys"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    
    # 关系定义
    provider: LLMProvider = Relationship(back_populates="api_keys")


# ==================== 响应模型 ====================

class ModelResponse(SQLModel):
    """模型响应模型"""
    id: int
    name: str
    llm_type: LLMType
    description: Optional[str] = None
    is_enabled: bool = True
    providers: List[Dict[str, Any]] = []
    parameters: List[Dict[str, Any]] = []
    created_at: datetime
    updated_at: datetime


class ProviderResponse(SQLModel):
    """提供商响应模型"""
    id: int
    name: str
    provider_type: ProviderType
    official_endpoint: Optional[str] = None
    third_party_endpoint: Optional[str] = None
    description: Optional[str] = None
    is_enabled: bool = True
    models: List[Dict[str, Any]] = []
    api_keys_count: int = 0
    created_at: datetime
    updated_at: datetime


class ModelProviderResponse(LLMModelProviderBase):
    """模型-提供商关联响应模型"""
    id: int
    model_name: str
    provider_name: str
    
    class Config:
        protected_namespaces = ()


# ==================== 请求模型 ====================

class ModelCreateRequest(LLMModelBase):
    """创建模型请求"""
    provider_id: Optional[int] = None
    provider_weight: int = Field(default=10, ge=1, le=100)
    is_provider_preferred: bool = Field(default=False)
    capability_ids: Optional[List[int]] = Field(default=None)


class ProviderCreateRequest(LLMProviderBase):
    """创建提供商请求"""
    api_key: Optional[str] = Field(default=None, max_length=500)


class ModelProviderCreateRequest(LLMModelProviderBase):
    """创建模型-提供商关联请求"""
    pass


class ModelProviderUpdateRequest(SQLModel):
    """更新模型-提供商关联请求"""
    weight: Optional[int] = Field(default=None, ge=1, le=100)
    priority: Optional[int] = Field(default=None, ge=0, le=100)
    is_enabled: Optional[bool] = Field(default=None)
    is_preferred: Optional[bool] = Field(default=None)
    health_status: Optional[HealthStatus] = Field(default=None)


class LLMModelParamCreateRequest(SQLModel):
    """创建模型参数请求"""
    llm_id: int
    provider_id: Optional[int] = None
    param_key: str
    param_value: Any
    is_enabled: bool = True
    description: Optional[str] = None


class LLMProviderApiKeyCreateRequest(SQLModel):
    """创建API密钥请求"""
    provider_id: int
    name: Optional[str] = None
    api_key: str
    is_enabled: bool = True
    is_preferred: bool = False
    weight: int = 10
    daily_quota: Optional[int] = None
    usage_count: int = 0
    description: Optional[str] = None


# ==================== 能力相关模型 ====================

class CapabilityBase(SQLModel):
    """能力基础类"""
    capability_name: str = Field(max_length=50, unique=True, index=True)
    description: Optional[str] = Field(default=None)


class Capability(CapabilityBase, table=True):
    """能力表 - 匹配实际数据库结构（无时间戳字段）"""
    __tablename__ = "capabilities"
    
    capability_id: Optional[int] = Field(default=None, primary_key=True)
    
    # 关系定义
    llm_models: List["LLMModelCapability"] = Relationship(back_populates="capability")


class LLMModelCapabilityBase(SQLModel):
    """模型-能力关联基础类"""
    model_id: int = Field(foreign_key="llm_models.id", primary_key=True)
    capability_id: int = Field(foreign_key="capabilities.capability_id", primary_key=True)
    
    class Config:
        protected_namespaces = ()


class LLMModelCapability(LLMModelCapabilityBase, table=True):
    """模型-能力关联表（多对多关系）"""
    __tablename__ = "llm_model_capabilities"
    
    # 关系定义
    llm_model: LLMModel = Relationship(back_populates="capabilities")
    capability: Capability = Relationship(back_populates="llm_models")


# 更新LLMModel以包含capabilities关系
LLMModel.model_rebuild()


# ==================== 查询优化类 ====================

class QueryBuilder:
    """查询构建器 - 提供复杂查询的构建方法"""
    
    @staticmethod
    def get_models_with_healthy_providers():
        """获取有健康提供商的模型"""
        return (
            select(LLMModel)
            .join(LLMModelProvider)
            .where(
                LLMModel.is_enabled == True,
                LLMModelProvider.is_enabled == True,
                LLMModelProvider.health_status == HealthStatus.healthy
            )
            .distinct()
        )
    
    @staticmethod
    def get_top_performing_providers(limit: int = 10):
        """获取性能最佳的提供商"""
        return (
            select(LLMProvider, LLMModelProvider.overall_score.label('avg_score'))
            .join(LLMModelProvider)
            .where(
                LLMProvider.is_enabled == True,
                LLMModelProvider.is_enabled == True
            )
            .group_by(LLMProvider.id)
            .order_by(LLMModelProvider.overall_score.desc())
            .limit(limit)
        )
    
    @staticmethod
    def get_models_by_performance_threshold(min_score: float = 0.8):
        """获取性能超过阈值的模型"""
        return (
            select(LLMModel)
            .join(LLMModelProvider)
            .where(
                LLMModel.is_enabled == True,
                LLMModelProvider.overall_score >= min_score
            )
            .distinct()
        )


# ==================== 性能监控模型 ====================

class PerformanceMetrics(SQLModel):
    """性能指标模型"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    success_rate: float = 0.0
    total_cost: float = 0.0
    cost_per_request: float = 0.0


class HealthCheckResult(SQLModel):
    """健康检查结果模型"""
    status: HealthStatus
    response_time: float
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    extra_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
