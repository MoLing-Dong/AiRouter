from typing import Optional
from app.core.adapters.base import BaseAdapter
from app.core.adapters.openai import OpenAIAdapter
from app.core.adapters.anthropic import AnthropicAdapter
from app.core.adapters.volcengine import VolcengineAdapter
from config.settings import ModelProvider


class AdapterFactory:
    """适配器工厂 - 负责创建不同类型的适配器"""

    def create_adapter(
        self, provider_config: ModelProvider, model_name: str = None
    ) -> Optional[BaseAdapter]:
        """根据提供商配置创建适配器"""
        try:
            # 构建适配器配置
            adapter_config = {
                "provider": provider_config.name,
                "base_url": provider_config.base_url,
                "model": model_name
                or provider_config.name,  # 使用传入的模型名或提供商名
                "max_tokens": provider_config.max_tokens,
                "temperature": provider_config.temperature,
                "cost_per_1k_tokens": provider_config.cost_per_1k_tokens,
                "timeout": provider_config.timeout,
                "retry_count": provider_config.retry_count,
                "weight": provider_config.weight,
            }

            # 根据提供商类型创建适配器（大小写不敏感）
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
            elif provider_name_lower == "google":
                # TODO: 实现Google适配器
                print(f"警告: Google适配器尚未实现: {provider_config.name}")
                return None
            elif provider_name_lower == "private-server":
                # 私有服务器适配器
                return OpenAIAdapter(adapter_config, provider_config.api_key)
            else:
                # 默认使用OpenAI适配器（兼容第三方OpenAI兼容的API）
                print(f"使用OpenAI适配器作为默认适配器: {provider_config.name}")
                return OpenAIAdapter(adapter_config, provider_config.api_key)

        except Exception as e:
            print(f"创建适配器失败: {provider_config.name} - {e}")
            return None

    def _create_openai_adapter(self, config: dict, api_key: str) -> OpenAIAdapter:
        """创建OpenAI适配器"""
        return OpenAIAdapter(config, api_key)

    def _create_anthropic_adapter(self, config: dict, api_key: str) -> AnthropicAdapter:
        """创建Anthropic适配器"""
        return AnthropicAdapter(config, api_key)

    def _create_volcengine_adapter(
        self, config: dict, api_key: str
    ) -> VolcengineAdapter:
        """创建火山引擎适配器"""
        return VolcengineAdapter(config, api_key)
