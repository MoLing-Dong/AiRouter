from typing import Optional
from app.core.adapters.base import BaseAdapter
from app.core.adapters.openai import OpenAIAdapter
from app.core.adapters.anthropic import AnthropicAdapter
from app.core.adapters.volcengine import VolcengineAdapter
from app.core.adapters.zhipu import ZhipuAdapter
from app.core.adapters.aliqwen import AliQwenAdapter
from config.settings import ModelProvider
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class AdapterFactory:
    """Adapter factory - responsible for creating different types of adapters"""

    def create_adapter(
        self, provider_config: ModelProvider, model_name: str = None
    ) -> Optional[BaseAdapter]:
        """Create adapter based on provider configuration"""
        try:
            # Build adapter configuration
            adapter_config = {
                "provider": provider_config.name,
                "base_url": provider_config.base_url,
                "model": model_name
                or getattr(
                    provider_config, "model", provider_config.name
                ),  # 优先使用传入的模型名，然后从提供商配置获取，最后使用提供商名
                "max_tokens": provider_config.max_tokens,
                "temperature": provider_config.temperature,
                "cost_per_1k_tokens": provider_config.cost_per_1k_tokens,
                "timeout": provider_config.timeout,
                "retry_count": provider_config.retry_count,
                "weight": provider_config.weight,
            }

            logger.info(
                f"🔧 Creating adapter: {provider_config.name} -> model: {adapter_config['model']}"
            )

            # Create adapter based on provider type (case-insensitive)
            provider_name_lower = provider_config.name.lower()

            if (
                provider_name_lower.startswith("openai")
                or provider_name_lower == "azure-openai"
            ):
                return OpenAIAdapter(adapter_config, provider_config.api_key)
            elif provider_name_lower == "anthropic":
                return AnthropicAdapter(adapter_config, provider_config.api_key)
            elif provider_name_lower == "volcengine":
                return VolcengineAdapter(adapter_config, provider_config.api_key)
            elif provider_name_lower == "zhipu":
                return ZhipuAdapter(adapter_config, provider_config.api_key)
            elif provider_name_lower == "aliqwen":
                return AliQwenAdapter(adapter_config, provider_config.api_key)
            elif provider_name_lower == "google":
                # TODO: Implement Google adapter
                logger.info(f"Warning: Google adapter not implemented: {provider_config.name}")
                return None
            elif provider_name_lower == "private-server":
                # Private server adapter
                return OpenAIAdapter(adapter_config, provider_config.api_key)
            else:
                # Use OpenAI adapter as default (compatible with third-party OpenAI API)
                logger.info(f"Using OpenAI adapter as default adapter: {provider_config.name}")
                return OpenAIAdapter(adapter_config, provider_config.api_key)

        except Exception as e:
            logger.info(f"Failed to create adapter: {provider_config.name} - {e}")
            return None

    def _create_openai_adapter(self, config: dict, api_key: str) -> OpenAIAdapter:
        """Create OpenAI adapter"""
        return OpenAIAdapter(config, api_key)

    def _create_anthropic_adapter(self, config: dict, api_key: str) -> AnthropicAdapter:
        """Create Anthropic adapter"""
        return AnthropicAdapter(config, api_key)

    def _create_volcengine_adapter(
        self, config: dict, api_key: str
    ) -> VolcengineAdapter:
        """Create Volcengine adapter"""
        return VolcengineAdapter(config, api_key)

    def _create_zhipu_adapter(self, config: dict, api_key: str) -> ZhipuAdapter:
        """Create Zhipu adapter"""
        return ZhipuAdapter(config, api_key)

    def _create_aliqwen_adapter(self, config: dict, api_key: str) -> AliQwenAdapter:
        """Create AliQwen adapter"""
        return AliQwenAdapter(config, api_key)
