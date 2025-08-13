# Export base classes and interfaces
from .base import (
    BaseAdapter,
    ChatRequest,
    ChatResponse,
    Message,
    MessageRole,
    HealthStatus,
    ModelMetrics,
    Tool,
    FunctionCall,
)

# Export specific adapter implementations
from .openai import OpenAIAdapter
from .anthropic import AnthropicAdapter
from .volcengine import VolcengineAdapter
from .zhipu import ZhipuAdapter
from .aliqwen import AliQwenAdapter

# Export adapter factory functions
from ...services.adapter_factory import AdapterFactory

# Create global adapter factory instance
_adapter_factory = AdapterFactory()


def create_adapter(provider_name: str, config: dict):
    """Create adapter function"""
    from config.settings import ModelProvider

    # Create ModelProvider object
    provider_config = ModelProvider(
        name=provider_name,
        base_url=config.get("base_url", ""),
        api_key=config.get("api_key", ""),
        max_tokens=config.get("max_tokens", 4096),
        temperature=config.get("temperature", 0.7),
        cost_per_1k_tokens=config.get("cost_per_1k_tokens", 0.0),
        timeout=config.get("timeout", 30),
        retry_count=config.get("retry_count", 3),
        weight=config.get("weight", 1),
    )

    return _adapter_factory.create_adapter(provider_config, config.get("model"))


# Export all necessary classes
__all__ = [
    # Base classes and interfaces
    "BaseAdapter",
    "ChatRequest",
    "ChatResponse",
    "Message",
    "MessageRole",
    "HealthStatus",
    "ModelMetrics",
    "Tool",
    "FunctionCall",
    # Specific adapter implementations
    "OpenAIAdapter",
    "AnthropicAdapter",
    "VolcengineAdapter",
    "ZhipuAdapter",
    "AliQwenAdapter",
    # Adapter factory functions
    "create_adapter",
]
