from sqlalchemy import Column, BigInteger, String, Text
from sqlalchemy.orm import relationship

from .base import Base


class Capability(Base):
    """Capability type table"""

    __tablename__ = "capabilities"

    capability_id = Column(BigInteger, primary_key=True, autoincrement=True)
    capability_name = Column(
        String(50), unique=True, nullable=False
    )  # Capability name (uppercase)
    description = Column(Text)  # Capability description
    # Relationships
    llm_models = relationship("LLMModelCapability", back_populates="capability")
