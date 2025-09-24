# Import SQLModel models and components
from .sqlmodel_models import (
    # Enums
    HealthStatus,
    HealthStatusEnum,  # backward compatibility
    LLMType,
    LLMTypeEnum,      # backward compatibility  
    ProviderType,
    ProviderTypeEnum, # backward compatibility
    
    # Table models
    LLMModel,
    LLMProvider,
    LLMProviderApiKey,
    LLMModelProvider,
    LLMModelParam,
    Capability,
    LLMModelCapability,
    
    # Request/Response models
    ModelCreateRequest as LLMModelCreate,
    ProviderCreateRequest as LLMProviderCreate,
    ModelProviderCreateRequest as LLMModelProviderCreate,
    ModelProviderUpdateRequest as LLMModelProviderUpdate,
    LLMModelParamCreateRequest as LLMModelParamCreate,
    LLMProviderApiKeyCreateRequest as LLMProviderApiKeyCreate,
    ModelResponse,
    ProviderResponse,
    ModelProviderResponse,
    
    # Utility classes
    QueryBuilder,
    PerformanceMetrics,
    HealthCheckResult,
    TimestampMixin
)

# Export all models
__all__ = [
    # Enums
    "HealthStatus",
    "HealthStatusEnum",  # backward compatibility
    "LLMType", 
    "LLMTypeEnum",      # backward compatibility
    "ProviderType",
    "ProviderTypeEnum", # backward compatibility
    
    # Table models
    "LLMModel",
    "LLMProvider",
    "LLMProviderApiKey",
    "LLMModelProvider",
    "LLMModelParam",
    "Capability",
    "LLMModelCapability",
    
    # Request models (for backward compatibility)
    "LLMModelCreate",
    "LLMProviderCreate", 
    "LLMModelProviderCreate",
    "LLMModelProviderUpdate",
    "LLMModelParamCreate",
    "LLMProviderApiKeyCreate",
    
    # Response models
    "ModelResponse",
    "ProviderResponse",
    "ModelProviderResponse",
    
    # Utility classes
    "QueryBuilder",
    "PerformanceMetrics",
    "HealthCheckResult",
    "TimestampMixin"
]
