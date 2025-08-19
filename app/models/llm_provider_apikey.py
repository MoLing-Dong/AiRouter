from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Boolean,
    Text,
    DateTime,
    Integer,
    ForeignKey,
    CheckConstraint,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base


class LLMProviderApiKey(Base):
    """LLM provider API key table"""

    __tablename__ = "llm_provider_apikeys"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    provider_id = Column(
        BigInteger,
        ForeignKey("llm_providers.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = Column(String(100))
    api_key = Column(Text, nullable=False)
    is_enabled = Column(Boolean, default=True)
    is_preferred = Column(Boolean, default=False)
    weight = Column(Integer, default=10)
    daily_quota = Column(Integer)
    usage_count = Column(Integer, default=0)
    description = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # Relationships
    provider = relationship("LLMProvider", back_populates="api_keys")

    __table_args__ = (
        CheckConstraint("weight > 0", name="provider_apikey_weight_check"),
        Index(
            "idx_apikey_provider_enabled_weight", "provider_id", "is_enabled", "weight"
        ),
    )
