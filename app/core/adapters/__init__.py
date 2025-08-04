from typing import Dict, Any, Optional, List
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
from .openai import OpenAIAdapter
from .anthropic import AnthropicAdapter
from .volcengine import VolcengineAdapter
from config.settings import ModelConfig, ModelProvider
import os


class ModelAdapterManager:
    """模型适配器管理器 - 以模型为主的设计"""

    def __init__(self):
        self.model_configs: Dict[str, ModelConfig] = {}
        self.model_adapters: Dict[str, List[BaseAdapter]] = {}
        self.provider_adapters: Dict[str, BaseAdapter] = {}
        self.use_database: bool = True  # 是否使用数据库配置

    def set_use_database(self, use_db: bool):
        """设置是否使用数据库配置"""
        self.use_database = use_db

    def load_models_from_database(self):
        """从数据库加载所有模型配置"""
        if not self.use_database:
            return

        try:
            # 延迟导入数据库服务，避免循环导入
            from app.services.database_service import db_service

            # 从数据库获取所有模型配置
            db_configs = db_service.get_all_model_configs_from_db()
            print(f"从数据库加载的模型配置: {list(db_configs.keys())}")

            # 清除现有配置
            self.model_configs.clear()
            self.model_adapters.clear()
            self.provider_adapters.clear()

            # 注册从数据库获取的模型
            for model_name, config in db_configs.items():
                print(f"注册模型: {model_name}")
                self._register_model_from_dict(model_name, config)

            print(f"最终可用模型: {list(self.model_configs.keys())}")

        except Exception as e:
            print(f"从数据库加载模型配置失败: {e}")
            import traceback

            traceback.print_exc()

    def _register_model_from_dict(self, model_name: str, config_dict: Dict[str, Any]):
        """从字典注册模型配置"""
        try:
            # 构建ModelConfig对象
            providers = []
            for provider_dict in config_dict.get("providers", []):
                # 从数据库获取API密钥
                api_key = self._get_api_key_from_database(provider_dict["name"])
                if not api_key:
                    print(f"警告: 未找到提供商 {provider_dict['name']} 的API密钥")
                    continue

                provider = ModelProvider(
                    name=provider_dict["name"],
                    base_url=provider_dict["base_url"],
                    api_key=api_key,
                    weight=provider_dict.get("weight", 1.0),
                    max_tokens=provider_dict.get("max_tokens", 4096),
                    temperature=provider_dict.get("temperature", 0.7),
                    cost_per_1k_tokens=provider_dict.get("cost_per_1k_tokens", 0.0),
                    timeout=provider_dict.get("timeout", 30),
                    retry_count=provider_dict.get("retry_count", 3),
                    enabled=provider_dict.get("enabled", True),
                )
                providers.append(provider)

            if not providers:
                print(f"警告: 模型 {model_name} 没有可用的提供商")
                return

            model_config = ModelConfig(
                name=model_name,
                providers=providers,
                model_type=config_dict.get("model_type", "chat"),
                max_tokens=config_dict.get("max_tokens", 4096),
                temperature=config_dict.get("temperature", 0.7),
                top_p=config_dict.get("top_p", 1.0),
                frequency_penalty=config_dict.get("frequency_penalty", 0.0),
                presence_penalty=config_dict.get("presence_penalty", 0.0),
                enabled=config_dict.get("enabled", True),
                priority=config_dict.get("priority", 0),
            )

            self.register_model(model_name, model_config)
            print(f"✅ 从数据库注册模型: {model_name}")

        except Exception as e:
            print(f"注册模型失败 {model_name}: {e}")

    def _get_api_key_from_database(self, provider_name: str) -> str:
        """从数据库获取提供商的最佳API密钥"""
        try:
            # 延迟导入数据库服务，避免循环导入
            from app.services.database_service import db_service

            # 根据提供商名称获取提供商
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                print(f"警告: 数据库中未找到提供商: {provider_name}")
                return ""

            # 获取最佳API密钥
            api_key_obj = db_service.get_best_api_key(provider.id)
            if not api_key_obj:
                print(f"警告: 提供商 {provider_name} 没有可用的API密钥")
                return ""

            return api_key_obj.api_key

        except Exception as e:
            print(f"从数据库获取API密钥失败: {provider_name} - {e}")
            return ""

    def _get_api_key_for_provider(self, provider_name: str) -> str:
        """根据提供商名称获取API密钥（兼容性方法，优先从数据库获取）"""
        # 首先尝试从数据库获取
        api_key = self._get_api_key_from_database(provider_name)
        if api_key:
            return api_key

        # 如果数据库中没有，则从settings获取（作为备用）
        from config.settings import settings

        # 尝试从settings获取API密钥
        api_key_attr = f"{provider_name.upper().replace('-', '_')}_API_KEY"
        api_key = getattr(settings, api_key_attr, "")

        if not api_key:
            # 尝试其他常见的API密钥属性名
            common_attrs = [
                f"{provider_name.upper()}_API_KEY",
                f"{provider_name.replace('-', '_').upper()}_API_KEY",
                f"{provider_name.replace('-', '').upper()}_API_KEY",
            ]

            for attr in common_attrs:
                api_key = getattr(settings, attr, "")
                if api_key:
                    break

        return api_key

    def register_model(self, model_name: str, model_config: ModelConfig):
        """注册模型配置"""
        self.model_configs[model_name] = model_config
        self.model_adapters[model_name] = []

        # 为每个提供商创建适配器
        for provider_config in model_config.providers:
            if not provider_config.enabled:
                continue

            adapter = self._create_provider_adapter(provider_config, model_name)
            if adapter:
                self.model_adapters[model_name].append(adapter)
                self.provider_adapters[f"{model_name}:{provider_config.name}"] = adapter

    def _create_provider_adapter(
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
                return None
            elif provider_name_lower == "private-server":
                # 私有服务器适配器
                return OpenAIAdapter(adapter_config, provider_config.api_key)
            else:
                # 默认使用OpenAI适配器（兼容第三方OpenAI兼容的API）
                return OpenAIAdapter(adapter_config, provider_config.api_key)

        except Exception as e:
            print(f"创建适配器失败: {provider_config.name} - {e}")
            return None

    def get_model_adapters(self, model_name: str) -> List[BaseAdapter]:
        """获取模型的所有适配器"""
        return self.model_adapters.get(model_name, [])

    def get_best_adapter(self, model_name: str) -> Optional[BaseAdapter]:
        """获取模型的最佳适配器（基于权重和健康状态）"""
        adapters = self.get_model_adapters(model_name)
        if not adapters:
            return None

        # 按权重和健康状态排序
        scored_adapters = []
        for adapter in adapters:
            score = (
                adapter.metrics.cost_per_1k_tokens * 0.3
                + (1 - adapter.metrics.response_time / 10) * 0.4
                + adapter.metrics.success_rate * 0.3
            )

            # 考虑权重
            weight = getattr(adapter, "weight", 1.0)
            score *= weight

            # 考虑健康状态
            if adapter.health_status == HealthStatus.HEALTHY:
                score *= 1.2
            elif adapter.health_status == HealthStatus.DEGRADED:
                score *= 0.8
            else:
                score *= 0.3

            scored_adapters.append((adapter, score))

        # 返回得分最高的适配器
        scored_adapters.sort(key=lambda x: x[1], reverse=True)
        return scored_adapters[0][0] if scored_adapters else None

    def get_available_models(self) -> List[str]:
        """获取所有可用模型"""
        return list(self.model_configs.keys())

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """获取模型配置"""
        return self.model_configs.get(model_name)

    async def health_check_model(self, model_name: str) -> Dict[str, str]:
        """检查模型的所有适配器健康状态"""
        health_status = {}
        adapters = self.get_model_adapters(model_name)

        for adapter in adapters:
            try:
                print(f"检查适配器: {type(adapter).__name__} - {adapter.provider}")
                status = await adapter.health_check()
                print(f"健康状态: {status.value}")
                health_status[f"{model_name}:{adapter.provider}"] = status.value
            except Exception:
                health_status[f"{model_name}:{adapter.provider}"] = "unhealthy"

        return health_status

    async def health_check_all(self) -> Dict[str, str]:
        """检查所有模型的健康状态"""
        all_health_status = {}
        for model_name in self.get_available_models():
            model_health = await self.health_check_model(model_name)
            all_health_status.update(model_health)
        return all_health_status

    async def close_all(self):
        """关闭所有适配器"""
        for adapters in self.model_adapters.values():
            for adapter in adapters:
                await adapter.close()
        self.model_adapters.clear()
        self.provider_adapters.clear()

    def refresh_from_database(self):
        """从数据库刷新模型配置"""
        self.load_models_from_database()


# 全局适配器管理器实例
adapter_manager = ModelAdapterManager()


# 兼容性函数
def get_adapter(model_name: str) -> Optional[BaseAdapter]:
    """获取模型的最佳适配器"""
    return adapter_manager.get_best_adapter(model_name)


def register_model(model_name: str, model_config: ModelConfig):
    """注册模型配置"""
    adapter_manager.register_model(model_name, model_config)


async def chat_completion(model_name: str, request: ChatRequest) -> ChatResponse:
    """执行聊天完成"""
    adapter = get_adapter(model_name)
    if not adapter:
        raise ValueError(f"没有可用的适配器: {model_name}")
    return await adapter.chat_completion(request)


# 导出所有必要的类
__all__ = [
    "BaseAdapter",
    "ChatRequest",
    "ChatResponse",
    "Message",
    "MessageRole",
    "HealthStatus",
    "ModelMetrics",
    "Tool",
    "FunctionCall",
    "OpenAIAdapter",
    "AnthropicAdapter",
    "VolcengineAdapter",
    "ModelAdapterManager",
    "adapter_manager",
    "get_adapter",
    "register_model",
    "chat_completion",
]
