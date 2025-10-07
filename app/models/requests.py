"""
请求模型定义
包含所有API请求的数据模型
"""

from sqlmodel import SQLModel, Field
from typing import Optional, List
from .sqlmodel_models import (
    LLMModelBase,
    LLMProviderBase,
    LLMModelProviderBase,
    LLMType,
    ProviderType,
    HealthStatus,
)


# ==================== 模型相关请求 ====================


class ModelCreateRequest(LLMModelBase):
    """创建模型请求"""

    provider_id: Optional[int] = None
    provider_weight: int = Field(default=10, ge=1, le=100)
    is_provider_preferred: bool = Field(default=False)
    capability_ids: Optional[List[int]] = Field(default=None)


class ModelUpdateRequest(SQLModel):
    """更新模型请求（所有字段可选）"""

    name: Optional[str] = Field(default=None, max_length=100)
    llm_type: Optional[LLMType] = Field(default=None)
    description: Optional[str] = Field(default=None)
    is_enabled: Optional[bool] = Field(default=None)

    # 更新能力关联
    capability_ids: Optional[List[int]] = Field(
        default=None, description="模型能力ID列表"
    )

    # 更新提供商关联
    provider_id: Optional[int] = Field(default=None, description="提供商ID")
    provider_weight: Optional[int] = Field(
        default=None, ge=1, le=100, description="提供商权重"
    )
    is_provider_preferred: Optional[bool] = Field(
        default=None, description="是否为优先提供商"
    )


# ==================== 提供商相关请求 ====================


class ProviderCreateRequest(LLMProviderBase):
    """创建提供商请求"""

    api_key: Optional[str] = Field(default=None, max_length=500)


class ProviderUpdateRequest(SQLModel):
    """更新提供商请求（所有字段可选）"""

    name: Optional[str] = Field(default=None, max_length=100)
    provider_type: Optional[ProviderType] = Field(default=None)
    official_endpoint: Optional[str] = Field(default=None, max_length=255)
    description: Optional[str] = Field(default=None)
    is_enabled: Optional[bool] = Field(default=None)


# ==================== 模型-提供商关联请求 ====================


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


# ==================== API密钥相关请求 ====================


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
