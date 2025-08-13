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
            logger.info(f"Model configurations loaded from database: {list(db_configs.keys())}")

            # Clear existing configurations
            self.model_configs.clear()
            self.model_adapters.clear()
            self.provider_adapters.clear()

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
                    logger.info(f"Warning: No API key found for provider {provider_dict['name']}")
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

    def get_model_adapters(self, model_name: str) -> List[BaseAdapter]:
        """Get all adapters for the model"""
        return self.model_adapters.get(model_name, [])

    def get_best_adapter(self, model_name: str) -> Optional[BaseAdapter]:
        """Get best adapter for the model (based on weight and health status)"""
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

    def get_available_models(self) -> List[str]:
        """Get all available models"""
        return list(self.model_configs.keys())

    def get_model_config(self, model_name: str) -> Optional[ModelConfig]:
        """Get model configuration"""
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
