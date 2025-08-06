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
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


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
