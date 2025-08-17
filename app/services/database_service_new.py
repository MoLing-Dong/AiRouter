"""
New Database Service
使用重构后的服务架构提供数据库操作
"""

from app.services.service_factory import ServiceFactory
from app.services.base.transaction_manager import DatabaseTransactionManager
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class DatabaseService:
    """New database service using the refactored architecture"""

    def __init__(self, session_factory):
        self.service_factory = ServiceFactory(session_factory)
        self.tx_manager = self.service_factory.transaction_manager

        # Get service instances
        self.model_service = self.service_factory.get_model_service()
        self.provider_service = self.service_factory.get_provider_service()
        self.model_provider_service = self.service_factory.get_model_provider_service()
        self.api_key_service = self.service_factory.get_api_key_service()

        logger.info("🚀 New Database Service initialized with refactored architecture")

    # Model operations
    def create_model(self, model_data):
        """Create model with optional provider association"""
        return self.model_service.create_model(model_data)

    def get_model(self, model_id):
        """Get model by ID"""
        return self.model_service.get_model(model_id)

    def get_model_by_name(self, name):
        """Get model by name"""
        return self.model_service.get_model_by_name(name)

    def get_all_models(self, enabled_only=True):
        """Get all models"""
        return self.model_service.get_all_models(enabled_only)

    def get_models_by_type(self, model_type):
        """Get models by type"""
        return self.model_service.get_models_by_type(model_type)

    def update_model(self, model_id, update_data):
        """Update model"""
        return self.model_service.update_model(model_id, update_data)

    def delete_model(self, model_id):
        """Delete model"""
        return self.model_service.delete_model(model_id)

    def enable_model(self, model_id):
        """Enable model"""
        return self.model_service.enable_model(model_id)

    def disable_model(self, model_id):
        """Disable model"""
        return self.model_service.disable_model(model_id)

    def get_model_with_providers(self, model_id):
        """Get model with its provider associations"""
        return self.model_service.get_model_with_providers(model_id)

    def search_models(self, search_term, model_type=None):
        """Search models"""
        return self.model_service.search_models(search_term, model_type)

    def get_model_statistics(self):
        """Get model statistics"""
        return self.model_service.get_model_statistics()

    # Provider operations
    def create_provider(self, provider_data):
        """Create provider"""
        return self.provider_service.create_provider(provider_data)

    def get_provider(self, provider_id):
        """Get provider by ID"""
        return self.provider_service.get_provider(provider_id)

    def get_provider_by_name(self, name):
        """Get provider by name"""
        return self.provider_service.get_provider_by_name(name)

    def get_all_providers(self, enabled_only=True):
        """Get all providers"""
        return self.provider_service.get_all_providers(enabled_only)

    def get_providers_by_type(self, provider_type):
        """Get providers by type"""
        return self.provider_service.get_providers_by_type(provider_type)

    def update_provider(self, provider_id, update_data):
        """Update provider"""
        return self.provider_service.update_provider(provider_id, update_data)

    def delete_provider(self, provider_id):
        """Delete provider"""
        return self.provider_service.delete_provider(provider_id)

    def enable_provider(self, provider_id):
        """Enable provider"""
        return self.provider_service.enable_provider(provider_id)

    def disable_provider(self, provider_id):
        """Disable provider"""
        return self.provider_service.disable_provider(provider_id)

    def get_provider_with_models(self, provider_id):
        """Get provider with its model associations"""
        return self.provider_service.get_provider_with_models(provider_id)

    def search_providers(self, search_term, provider_type=None):
        """Search providers"""
        return self.provider_service.search_providers(search_term, provider_type)

    def get_provider_statistics(self):
        """Get provider statistics"""
        return self.provider_service.get_provider_statistics()

    def get_provider_endpoints(self, provider_id):
        """Get provider endpoints"""
        return self.provider_service.get_provider_endpoints(provider_id)

    def get_providers_by_model(self, model_id):
        """Get all providers associated with a model"""
        return self.provider_service.get_providers_by_model(model_id)

    def get_best_provider_for_model(self, model_id):
        """Get best provider for a model based on weight and preference"""
        return self.provider_service.get_best_provider_for_model(model_id)

    def validate_provider_availability(self, provider_id):
        """Validate provider availability and health"""
        return self.provider_service.validate_provider_availability(provider_id)

    # Model-Provider association operations
    def create_model_provider(self, association_data):
        """Create model-provider association"""
        return self.model_provider_service.create_association(association_data)

    def get_model_provider(self, association_id):
        """Get association by ID"""
        return self.model_provider_service.get_association(association_id)

    def get_model_providers_by_model(self, model_id, enabled_only=True):
        """Get all associations for a model"""
        return self.model_provider_service.get_associations_by_model(
            model_id, enabled_only
        )

    def get_model_providers_by_provider(self, provider_id, enabled_only=True):
        """Get all associations for a provider"""
        return self.model_provider_service.get_associations_by_provider(
            provider_id, enabled_only
        )

    def get_all_model_providers(self, enabled_only=True):
        """Get all associations"""
        return self.model_provider_service.get_all_associations(enabled_only)

    def update_model_provider(self, association_id, update_data):
        """Update association"""
        return self.model_provider_service.update_association(
            association_id, update_data
        )

    def delete_model_provider(self, association_id):
        """Delete association"""
        return self.model_provider_service.delete_association(association_id)

    def update_association_weight(self, association_id, new_weight):
        """Update association weight"""
        return self.model_provider_service.update_weight(association_id, new_weight)

    def update_association_preferred(self, association_id, is_preferred):
        """Update association preferred status"""
        return self.model_provider_service.update_preferred_status(
            association_id, is_preferred
        )

    def get_best_provider_association(self, model_id):
        """Get best provider association for a model"""
        return self.model_provider_service.get_best_provider_for_model(model_id)

    def get_detailed_association(self, model_id, provider_id):
        """Get detailed association information"""
        return self.model_provider_service.get_detailed_association(
            model_id, provider_id
        )

    def get_association_statistics(self):
        """Get association statistics"""
        return self.model_provider_service.get_association_statistics()

    def bulk_update_association_weights(self, updates):
        """Bulk update association weights"""
        return self.model_provider_service.bulk_update_weights(updates)

    def enable_association(self, association_id):
        """Enable association"""
        return self.model_provider_service.enable_association(association_id)

    def disable_association(self, association_id):
        """Disable association"""
        return self.model_provider_service.disable_association(association_id)

    def get_model_provider_matrix(self):
        """Get a matrix view of all model-provider associations"""
        return self.model_provider_service.get_model_provider_matrix()

    def validate_association_health(self, model_id, provider_id):
        """Validate the health of a specific association"""
        return self.model_provider_service.validate_association_health(
            model_id, provider_id
        )

    # API Key operations
    def create_api_key(self, api_key_data):
        """Create API key"""
        return self.api_key_service.create_api_key(api_key_data)

    def get_api_key(self, api_key_id):
        """Get API key by ID"""
        return self.api_key_service.get_api_key(api_key_id)

    def get_api_keys_by_provider(self, provider_id, enabled_only=True):
        """Get all API keys for a provider"""
        return self.api_key_service.get_api_keys_by_provider(provider_id, enabled_only)

    def get_best_api_key(self, provider_id):
        """Get best API key for a provider"""
        return self.api_key_service.get_best_api_key(provider_id)

    def update_api_key(self, api_key_id, update_data):
        """Update API key"""
        return self.api_key_service.update_api_key(api_key_id, update_data)

    def delete_api_key(self, api_key_id):
        """Delete API key"""
        return self.api_key_service.delete_api_key(api_key_id)

    def update_api_key_usage(self, api_key_id, increment=True):
        """Update API key usage count"""
        return self.api_key_service.update_usage_count(api_key_id, increment)

    def enable_api_key(self, api_key_id):
        """Enable API key"""
        return self.api_key_service.enable_api_key(api_key_id)

    def disable_api_key(self, api_key_id):
        """Disable API key"""
        return self.api_key_service.disable_api_key(api_key_id)

    def update_api_key_preferred(self, api_key_id, is_preferred):
        """Update API key preferred status"""
        return self.api_key_service.update_preferred_status(api_key_id, is_preferred)

    def get_api_key_statistics(self, provider_id=None):
        """Get API key statistics"""
        return self.api_key_service.get_api_key_statistics(provider_id)

    def check_api_key_quota(self, api_key_id):
        """Check if API key daily quota is exceeded"""
        return self.api_key_service.check_quota_exceeded(api_key_id)

    def reset_provider_daily_usage(self, provider_id):
        """Reset daily usage count for all API keys of a provider"""
        return self.api_key_service.reset_daily_usage(provider_id)

    def get_api_keys_by_endpoint(self, base_url):
        """Get API keys by base URL"""
        return self.api_key_service.get_api_keys_by_endpoint(base_url)

    def rotate_api_key(self, api_key_id, new_api_key):
        """Rotate API key"""
        return self.api_key_service.rotate_api_key(api_key_id, new_api_key)

    def get_available_api_keys(self, provider_id):
        """Get available API keys for a provider"""
        return self.api_key_service.get_available_api_keys_for_provider(provider_id)

    def get_api_key_health(self, api_key_id):
        """Get comprehensive health status of an API key"""
        return self.api_key_service.get_api_key_health_status(api_key_id)

    def bulk_update_api_keys(self, updates):
        """Bulk update multiple API keys"""
        return self.api_key_service.bulk_update_api_keys(updates)

    # Service management
    def get_service_factory(self):
        """Get service factory instance"""
        return self.service_factory

    def health_check(self):
        """Perform health check on all services"""
        return self.service_factory.health_check()

    def get_service_info(self):
        """Get information about all services"""
        return self.service_factory.get_service_info()

    def reset_services(self):
        """Reset all services"""
        self.service_factory.reset_services()
        # Re-initialize this service
        self.__init__(self.service_factory.session_factory)


# Create global instance
def create_database_service(session_factory):
    """Create a new database service instance"""
    return DatabaseService(session_factory)
