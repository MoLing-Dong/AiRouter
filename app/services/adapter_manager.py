import time
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

# Get logger
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class ModelAdapterManager:
    """Model adapter manager - designed around models"""

    def __init__(self):
        self.model_configs: Dict[str, ModelConfig] = {}
        self.model_adapters: Dict[str, List[BaseAdapter]] = {}
        self.provider_adapters: Dict[str, BaseAdapter] = {}
        self.use_database: bool = True
        # 添加配置时间戳缓存
        self.config_timestamps: Dict[str, float] = {}

        # Initialize services
        self.db_service = ModelDatabaseService()
        self.factory = AdapterFactory()
        self.health_checker = HealthChecker()

    def set_use_database(self, use_db: bool):
        """Set whether to use database configuration"""
        self.use_database = use_db

    def load_models_from_database(self):
        """Load all model configurations from database"""
        if not self.use_database:
            return

        try:
            # Get all model configurations from database
            db_configs = self.db_service.get_all_model_configs_from_db()
            logger.info(
                f"Model configurations loaded from database: {list(db_configs.keys())}"
            )

            # Clear existing configurations
            self.model_configs.clear()
            self.model_adapters.clear()
            self.provider_adapters.clear()
            self.config_timestamps.clear()

            # Register models from database
            for model_name, config in db_configs.items():
                logger.info(f"Registering model: {model_name}")
                self._register_model_from_dict(model_name, config)

            logger.info(f"Available models: {list(self.model_configs.keys())}")
            # Print adapter provider names for each model
            adapter_info = {}
            for model_name, adapters in self.model_adapters.items():
                adapter_info[model_name] = [adapter.provider for adapter in adapters]
            logger.info(f"Model providers: {adapter_info}")

        except Exception as e:
            logger.info(f"Failed to load model configurations from database: {e}")
            logger.info_exc()

    def _register_model_from_dict(self, model_name: str, config_dict: Dict[str, Any]):
        """Register model configuration from dictionary"""
        try:
            # Build ModelConfig object
            providers = []
            for provider_dict in config_dict.get("providers", []):
                # Get API key from database
                api_key = self.db_service.get_api_key_for_provider(
                    provider_dict["name"]
                )
                if not api_key:
                    logger.info(
                        f"Warning: No API key found for provider {provider_dict['name']}"
                    )
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
                logger.info(f"Warning: Model {model_name} has no available providers")
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
            # 记录配置时间戳
            self.config_timestamps[model_name] = config_dict.get(
                "updated_at", time.time()
            )
            logger.info(f"✅ Registered model from database: {model_name}")

        except Exception as e:
            logger.info(f"Failed to register model {model_name}: {e}")

    def register_model(self, model_name: str, model_config: ModelConfig):
        """Register model configuration"""
        self.model_configs[model_name] = model_config
        self.model_adapters[model_name] = []

        # Create adapter for each provider
        for provider_config in model_config.providers:
            if not provider_config.enabled:
                continue

            # Get model name from database configuration
            adapter_model_name = model_name
            adapter = self.factory.create_adapter(provider_config, adapter_model_name)
            if adapter:
                self.model_adapters[model_name].append(adapter)
                self.provider_adapters[f"{model_name}:{provider_config.name}"] = adapter

    def _check_config_version(self, model_name: str) -> bool:
        """检查模型配置是否需要刷新"""
        if not self.use_database:
            return False

        try:
            # 从数据库获取最新配置时间戳
            db_timestamp = self.db_service.get_model_updated_timestamp(model_name)
            if not db_timestamp:
                return False

            cached_timestamp = self.config_timestamps.get(model_name, 0)

            # 如果数据库时间戳更新，则需要刷新
            if db_timestamp > cached_timestamp:
                logger.info(
                    f"配置已过期，需要刷新模型: {model_name} (缓存: {cached_timestamp}, 数据库: {db_timestamp})"
                )
                return True
            return False
        except Exception as e:
            logger.warning(f"检查配置版本失败 {model_name}: {e}")
            return False

    def _refresh_single_model(self, model_name: str):
        """刷新单个模型配置"""
        try:
            config_dict = self.db_service.get_model_config_by_name(model_name)
            if config_dict:
                # 移除旧的配置
                if model_name in self.model_configs:
                    del self.model_configs[model_name]
                if model_name in self.model_adapters:
                    del self.model_adapters[model_name]
                if model_name in self.config_timestamps:
                    del self.config_timestamps[model_name]

                # 重新注册模型
                self._register_model_from_dict(model_name, config_dict)
                logger.info(f"✅ 自动刷新模型配置: {model_name}")
            else:
                logger.warning(f"模型 {model_name} 在数据库中未找到")
        except Exception as e:
            logger.error(f"刷新模型 {model_name} 失败: {e}")

    def get_model_adapters(self, model_name: str) -> List[BaseAdapter]:
        """Get all adapters for the model"""
        # 检查配置是否需要刷新
        if self._check_config_version(model_name):
            self._refresh_single_model(model_name)

        return self.model_adapters.get(model_name, [])

    def get_best_adapter(self, model_name: str) -> Optional[BaseAdapter]:
        """Get best adapter for the model (based on weight and health status)"""
        # 检查配置是否需要刷新
        if self._check_config_version(model_name):
            self._refresh_single_model(model_name)

        adapters = self.get_model_adapters(model_name)
        logger.info(f"Number of adapters for model {model_name}: {len(adapters)}")
        if not adapters:
            logger.warning(f"Model {model_name} has no available adapters")
            return None

        # Sort by weight and health status
        scored_adapters = []
        for adapter in adapters:
            # Avoid division by zero error, if response_time is 0, use default value
            response_time = adapter.metrics.response_time or 1.0
            score = (
                adapter.metrics.cost_per_1k_tokens * 0.3
                + (1 - response_time / 10) * 0.4
                + adapter.metrics.success_rate * 0.3
            )

            # Consider weight
            weight = getattr(adapter, "weight", 1.0)
            score *= weight

            # Consider health status
            if adapter.health_status == HealthStatus.HEALTHY:
                score *= 1.2
            elif adapter.health_status == HealthStatus.DEGRADED:
                score *= 0.8
            else:
                score *= 0.3

            scored_adapters.append((adapter, score))

        # Return adapter with highest score
        scored_adapters.sort(key=lambda x: x[1], reverse=True)
        return scored_adapters[0][0] if scored_adapters else None

    def get_available_models(
        self,
        model_types: Optional[List[str]] = None,
        capabilities: Optional[List[str]] = None,
    ) -> List[str]:
        """Get available models filtered by model types or capabilities

        Args:
            model_types: List of model types to filter by.
                        Common types: "chat", "text", "multimodal", "embedding"
                        If None, returns all models
            capabilities: List of capability names to filter by.
                        Common capabilities: "TEXT", "IMAGE", "VIDEO", "AUDIO",
                        "MULTIMODAL_IMAGE_UNDERSTANDING", "TEXT_TO_IMAGE", "IMAGE_TO_IMAGE"
                        If None, ignores capability filtering
        """
        # Get all models that pass the type and capability filters
        if not model_types and not capabilities:
            candidate_models = list(self.model_configs.keys())
        else:
            candidate_models = []
            for model_name, config in self.model_configs.items():
                # Check model type filter
                if model_types and config.model_type not in model_types:
                    continue

                # Check capability filter
                if capabilities:
                    model_capabilities = self._get_model_capabilities(model_name)
                    if not model_capabilities:
                        continue

                    # Check if model has any of the required capabilities
                    model_capability_names = [
                        cap["capability_name"] for cap in model_capabilities
                    ]
                    if not any(cap in model_capability_names for cap in capabilities):
                        continue

                candidate_models.append(model_name)

        # Filter models to only include those with at least one healthy provider
        available_models = []
        for model_name in candidate_models:
            adapters = self.get_model_adapters(model_name)
            if not adapters:
                continue
                
            # Check if model has at least one healthy adapter
            has_healthy_adapter = any(
                adapter.health_status == HealthStatus.HEALTHY 
                for adapter in adapters
            )
            
            if has_healthy_adapter:
                available_models.append(model_name)

        return available_models

    def get_available_models_fast(self, skip_version_check: bool = True) -> List[str]:
        """Get available models quickly without version checking (performance optimization)

        Args:
            skip_version_check: Whether to skip version checking for performance
        """
        if skip_version_check:
            # 快速获取可用模型，包含健康状态检查但不包含版本检查
            available_models = []
            for model_name in self.model_configs.keys():
                adapters = self.get_model_adapters(model_name)
                if not adapters:
                    continue
                    
                # Check if model has at least one healthy adapter
                has_healthy_adapter = any(
                    adapter.health_status == HealthStatus.HEALTHY 
                    for adapter in adapters
                )
                
                if has_healthy_adapter:
                    available_models.append(model_name)

            return available_models
        else:
            # 使用原有的方法，包含版本检查
            return self.get_available_models()

    def get_model_adapters_fast(
        self, model_name: str, skip_version_check: bool = True
    ) -> List[BaseAdapter]:
        """Get model adapters quickly without version checking (performance optimization)

        Args:
            model_name: Model name
            skip_version_check: Whether to skip version checking for performance
        """
        if skip_version_check:
            # 直接返回缓存的适配器，不进行版本检查
            return self.model_adapters.get(model_name, [])
        else:
            # 使用原有的方法，包含版本检查
            return self.get_model_adapters(model_name)

    def _get_model_capabilities(self, model_name: str) -> List[Dict[str, Any]]:
        """Get model capabilities from database"""
        try:
            from .database_service import db_service

            model = db_service.get_model_by_name(model_name)
            if model:
                return db_service.get_model_capabilities(model.id)
            return []
        except Exception as e:
            logger.info(f"Failed to get capabilities for model {model_name}: {e}")
            return []

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get model configuration"""
        # 检查配置是否需要刷新
        if self._check_config_version(model_name):
            self._refresh_single_model(model_name)

        return self.model_configs.get(model_name)

    async def health_check_model(self, model_name: str) -> Dict[str, str]:
        """Check health status for all adapters of the model"""
        return await self.health_checker.check_model_health(
            model_name, self.get_model_adapters(model_name)
        )

    async def health_check_all(self) -> Dict[str, str]:
        """Check health status for all models"""
        return await self.health_checker.check_all_models(
            self.get_available_models(), self.model_adapters
        )

    async def close_all(self):
        """Close all adapters"""
        for adapters in self.model_adapters.values():
            for adapter in adapters:
                await adapter.close()
        self.model_adapters.clear()
        self.provider_adapters.clear()

    def refresh_from_database(self):
        """Refresh model configurations from database"""
        self.load_models_from_database()

        # 通知相关服务清理缓存
        self._notify_cache_clear()

    def _notify_cache_clear(self):
        """通知相关服务清理缓存"""
        try:
            # 清理models接口的缓存
            from app.api.v1.models.cache_manager import models_cache

            models_cache.clear_cache()
            logger.info("✅ Notified models cache to clear")
        except Exception as e:
            logger.warning(f"Failed to notify cache clear: {e}")
