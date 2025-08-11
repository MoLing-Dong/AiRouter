# 导出基础类和接口
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

# 导出具体的适配器实现
from .openai import OpenAIAdapter
from .anthropic import AnthropicAdapter
from .volcengine import VolcengineAdapter
from .zhipu import ZhipuAdapter
from .aliqwen import AliQwenAdapter

# 导出适配器工厂函数
from ...services.adapter_factory import AdapterFactory

# 创建全局适配器工厂实例
_adapter_factory = AdapterFactory()


def create_adapter(provider_name: str, config: dict):
    """创建适配器的便捷函数"""
    from config.settings import ModelProvider

    # 创建 ModelProvider 对象
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


# 导出所有必要的类
__all__ = [
    # 基础类和接口
    "BaseAdapter",
    "ChatRequest",
    "ChatResponse",
    "Message",
    "MessageRole",
    "HealthStatus",
    "ModelMetrics",
    "Tool",
    "FunctionCall",
    # 具体适配器实现
    "OpenAIAdapter",
    "AnthropicAdapter",
    "VolcengineAdapter",
    "ZhipuAdapter",
    "AliQwenAdapter",
    # 适配器工厂函数
    "create_adapter",
]
