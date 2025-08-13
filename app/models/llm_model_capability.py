from sqlalchemy import Column, BigInteger, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base


class LLMModelCapability(Base):
    """Model-capability association table (many-to-many relationship)"""

    __tablename__ = "llm_model_capabilities"

    model_id = Column(
        BigInteger, ForeignKey("llm_models.id", ondelete="CASCADE"), primary_key=True
    )  # Foreign key to llm_models table
    capability_id = Column(
        BigInteger,
        ForeignKey("capabilities.capability_id", ondelete="CASCADE"),
        primary_key=True,
    )  # Foreign key to capabilities table

    # Relationships
    llm_model = relationship("LLMModel", back_populates="capabilities")
    capability = relationship("Capability", back_populates="llm_models")
