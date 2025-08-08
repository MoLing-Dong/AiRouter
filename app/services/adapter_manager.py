from typing import Dict, Any, Optional, List
from app.core.adapters.base import (
    BaseAdapter,
    ChatRequest,
    ChatResponse,
    HealthStatus,
)
from app.services.adapter_factory import AdapterFactory
from app.services.adapter_database_service import ModelDatabaseService
from app.services.adapter_health_checker import HealthChecker
from config.settings import ModelConfig, ModelProvider

# 获取日志器
from app.utils.logging_config import get_factory_logger

# 获取日志器
logger = get_factory_logger()

class ModelAdapterManager:
    """模型适配器管理器 - 以模型为主的设计"""

    def __init__(self):
        self.model_configs: Dict[str, ModelConfig] = {}
        self.model_adapters: Dict[str, List[BaseAdapter]] = {}
        self.provider_adapters: Dict[str, BaseAdapter] = {}
        self.use_database: bool = True

        # 初始化各个服务
        self.db_service = ModelDatabaseService()
        self.factory = AdapterFactory()
        self.health_checker = HealthChecker()

    def set_use_database(self, use_db: bool):
        """设置是否使用数据库配置"""
        self.use_database = use_db

    def load_models_from_database(self):
        """从数据库加载所有模型配置"""
        if not self.use_database:
            return

        try:
            # 从数据库获取所有模型配置
            db_configs = self.db_service.get_all_model_configs_from_db()
            logger.info(f"从数据库加载的模型配置: {list(db_configs.keys())}")

            # 清除现有配置
            self.model_configs.clear()
            self.model_adapters.clear()
            self.provider_adapters.clear()

            # 注册从数据库获取的模型
            for model_name, config in db_configs.items():
                logger.info(f"注册模型: {model_name}")
                self._register_model_from_dict(model_name, config)

            logger.info(f"最终可用模型: {list(self.model_configs.keys())}")

        except Exception as e:
            logger.info(f"从数据库加载模型配置失败: {e}")
            import traceback

            traceback.logger.info_exc()

    def _register_model_from_dict(self, model_name: str, config_dict: Dict[str, Any]):
        """从字典注册模型配置"""
        try:
            # 构建ModelConfig对象
            providers = []
            for provider_dict in config_dict.get("providers", []):
                # 从数据库获取API密钥
                api_key = self.db_service.get_api_key_for_provider(
                    provider_dict["name"]
                )
                if not api_key:
                    logger.info(f"警告: 未找到提供商 {provider_dict['name']} 的API密钥")
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
                logger.info(f"警告: 模型 {model_name} 没有可用的提供商")
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
            logger.info(f"✅ 从数据库注册模型: {model_name}")

        except Exception as e:
            logger.info(f"注册模型失败 {model_name}: {e}")

    def register_model(self, model_name: str, model_config: ModelConfig):
        """注册模型配置"""
        self.model_configs[model_name] = model_config
        self.model_adapters[model_name] = []

        # 为每个提供商创建适配器
        for provider_config in model_config.providers:
            if not provider_config.enabled:
                continue

            # 从数据库配置中获取模型名称
            adapter_model_name = model_name
            adapter = self.factory.create_adapter(provider_config, adapter_model_name)
            if adapter:
                self.model_adapters[model_name].append(adapter)
                self.provider_adapters[f"{model_name}:{provider_config.name}"] = adapter

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
        return await self.health_checker.check_model_health(
            model_name, self.get_model_adapters(model_name)
        )

    async def health_check_all(self) -> Dict[str, str]:
        """检查所有模型的健康状态"""
        return await self.health_checker.check_all_models(
            self.get_available_models(), self.model_adapters
        )

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
