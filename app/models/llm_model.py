from sqlalchemy import Column, BigInteger, String, Boolean, Text, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base
from .enums import LLMTypeEnum


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
