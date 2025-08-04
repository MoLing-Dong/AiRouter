from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
    Index,
    Enum,
    BigInteger,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from typing import List, Optional
import enum

Base = declarative_base()


# 枚举类型
class LLMTypeEnum(enum.Enum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class ProviderTypeEnum(enum.Enum):
    PUBLIC_CLOUD = "PUBLIC_CLOUD"
    THIRD_PARTY = "THIRD_PARTY"
    PRIVATE = "PRIVATE"


class ParamTypeEnum(enum.Enum):
    HYPERPARAMETER = "hyperparameter"
    CONFIG = "config"
    OTHER = "other"


class LLMModel(Base):
    """LLM模型表"""

    __tablename__ = "llm_models"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)
    llm_type = Column(Enum(LLMTypeEnum), nullable=False)
    description = Column(Text)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # 关系
    providers = relationship("LLMModelProvider", back_populates="llm_model")
    params = relationship("LLMModelParam", back_populates="llm_model")


class LLMProvider(Base):
    """LLM提供商表"""

    __tablename__ = "llm_providers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    provider_type = Column(Enum(ProviderTypeEnum), nullable=False)
    official_endpoint = Column(String(255))
    third_party_endpoint = Column(String(255))
    description = Column(Text)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # 关系
    models = relationship("LLMModelProvider", back_populates="provider")
    params = relationship("LLMModelParam", back_populates="provider")
    api_keys = relationship("LLMProviderApiKey", back_populates="provider")

    __table_args__ = (
        UniqueConstraint("name", "provider_type", name="uniq_provider_name_type"),
    )


class LLMProviderApiKey(Base):
    """LLM提供商API密钥表"""

    __tablename__ = "llm_provider_apikeys"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    provider_id = Column(
        BigInteger,
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100))
    api_key = Column(Text, nullable=False)
    base_url = Column(String(255))
    is_enabled = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)
    weight = Column(Integer, default=10)
    daily_quota = Column(Integer)
    usage_count = Column(Integer, default=0)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # 关系
    provider = relationship("LLMProvider", back_populates="api_keys")

    __table_args__ = (
        CheckConstraint("weight > 0", name="provider_apikey_weight_check"),
        Index(
            "idx_apikey_provider_enabled_weight", "provider_id", "is_enabled", "weight"
        ),
    )


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
        Index("idx_model_provider_llm", "llm_id"),
        Index("idx_model_provider_enabled_weight", "llm_id", "is_enabled", "weight"),
    )


class LLMModelParam(Base):
    """LLM模型参数表"""

    __tablename__ = "llm_model_params"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    llm_id = Column(
        BigInteger, ForeignKey("llm_models.id", ondelete="CASCADE"), nullable=False
    )
    provider_id = Column(BigInteger, ForeignKey("llm_providers.id", ondelete="CASCADE"))
    param_key = Column(String(100), nullable=False)
    param_value = Column(JSON)  # JSON类型，SQLite和PostgreSQL都支持
    param_type = Column(String(50))
    description = Column(Text)
    is_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=func.now())
    updated_at = Column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # 关系
    llm_model = relationship("LLMModel", back_populates="params")
    provider = relationship("LLMProvider", back_populates="params")

    __table_args__ = (
        UniqueConstraint(
            "llm_id",
            "provider_id",
            "param_key",
            name="model_param_llm_id_provider_id_param_key_key",
        ),
        Index("idx_param_llm_provider", "llm_id", "provider_id"),
        Index(
            "idx_param_llm_null_provider",
            "llm_id",
            postgresql_where="provider_id IS NULL AND is_enabled = true",
        ),
    )


# Pydantic模型用于API
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class LLMModelCreate(BaseModel):
    name: str
    llm_type: str
    description: Optional[str] = None
    is_enabled: bool = True


class LLMModelUpdate(BaseModel):
    name: Optional[str] = None
    llm_type: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class LLMProviderCreate(BaseModel):
    name: str
    provider_type: str
    official_endpoint: Optional[str] = None
    third_party_endpoint: Optional[str] = None
    description: Optional[str] = None
    is_enabled: bool = True


class LLMProviderUpdate(BaseModel):
    name: Optional[str] = None
    provider_type: Optional[str] = None
    official_endpoint: Optional[str] = None
    third_party_endpoint: Optional[str] = None
    description: Optional[str] = None
    is_enabled: Optional[bool] = None


class LLMProviderApiKeyCreate(BaseModel):
    provider_id: int
    name: Optional[str] = None
    api_key: str
    base_url: Optional[str] = None
    is_enabled: bool = True
    is_preferred: bool = False
    weight: int = 10
    daily_quota: Optional[int] = None
    description: Optional[str] = None


class LLMProviderApiKeyUpdate(BaseModel):
    name: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    is_enabled: Optional[bool] = None
    is_preferred: Optional[bool] = None
    weight: Optional[int] = None
    daily_quota: Optional[int] = None
    description: Optional[str] = None


class LLMModelProviderCreate(BaseModel):
    llm_id: int
    provider_id: int
    weight: int = 10
    is_preferred: bool = False
    is_enabled: bool = True


class LLMModelParamCreate(BaseModel):
    llm_id: int
    provider_id: Optional[int] = None
    param_key: str
    param_value: Dict[str, Any]  # JSON格式
    param_type: Optional[str] = None
    description: Optional[str] = None
    is_enabled: bool = True
