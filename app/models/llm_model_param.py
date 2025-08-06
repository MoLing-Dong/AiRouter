from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Index,
    JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


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
