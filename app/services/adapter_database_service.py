from typing import Dict, Any, Optional
from app.services.database_service import db_service
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()

class ModelDatabaseService:
    """Model database service - specifically handle database-related operations"""

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """Get all model configurations from database"""
        try:
            return db_service.get_all_model_configs_from_db()
        except Exception as e:
            logger.info(f"Failed to get model configurations from database: {e}")
            return {}

    def get_model_config_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get single model configuration by name"""
        try:
            return db_service.get_model_config_by_name(model_name)
        except Exception as e:
            logger.info(f"Failed to get model configuration for {model_name}: {e}")
            return None

    def get_model_updated_timestamp(self, model_name: str) -> Optional[float]:
        """Get model updated timestamp for version checking"""
        try:
            return db_service.get_model_updated_timestamp(model_name)
        except Exception as e:
            logger.info(f"Failed to get model timestamp for {model_name}: {e}")
            return None

    def get_api_key_for_provider(self, provider_name: str) -> str:
        """Get API key for provider (prioritize database)"""
        # First try to get from database
        api_key = self._get_api_key_from_database(provider_name)
        if api_key:
            return api_key

        # If not in database, get from settings (as fallback)
        return self._get_api_key_from_settings(provider_name)

    def _get_api_key_from_database(self, provider_name: str) -> str:
        """Get the best API key for provider from database"""
        try:
            # Get provider by name
            provider = db_service.get_provider_by_name(provider_name)
            if not provider:
                logger.info(f"警告: 数据库中未找到提供商: {provider_name}")
                return ""

            # Get best API key
            api_key_obj = db_service.get_best_api_key(provider.id)
            if not api_key_obj:
                logger.info(f"Warning: Provider {provider_name} has no available API key")
                return ""

            return api_key_obj.api_key

        except Exception as e:
            logger.info(f"Failed to get API key from database: {provider_name} - {e}")
            return ""

    def _get_api_key_from_settings(self, provider_name: str) -> str:
        """Get API key from settings (fallback)"""
        try:
            from config.settings import settings

            # Try to get API key from settings
            api_key_attr = f"{provider_name.upper().replace('-', '_')}_API_KEY"
            api_key = getattr(settings, api_key_attr, "")

            if not api_key:
                # Try other common API key attribute names
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

        except Exception as e:
            logger.info(f"Failed to get API key from settings: {provider_name} - {e}")
            return ""

    def get_provider_by_name(self, provider_name: str):
        """Get provider by name"""
        return db_service.get_provider_by_name(provider_name)

    def get_best_api_key(self, provider_id: int):
        """Get best API key"""
        return db_service.get_best_api_key(provider_id)
