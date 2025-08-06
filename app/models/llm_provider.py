from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Boolean,
    Text,
    DateTime,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
from .enums import ProviderTypeEnum


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
