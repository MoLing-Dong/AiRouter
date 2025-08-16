from typing import Optional
from .database_service import DatabaseService
from .model_service import ModelService
from .provider_service import ProviderService
from .model_provider_service import ModelProviderService
from .health_check_service import HealthCheckService
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ServiceManager:
    """Service manager for coordinating all services"""

    def __init__(self):
        # Initialize core database service
        self.db_service = DatabaseService()

        # Initialize specialized services
        self.model_service = ModelService(self.db_service)
        self.provider_service = ProviderService(self.db_service)
        self.model_provider_service = ModelProviderService(self.db_service)
        self.health_check_service = HealthCheckService(self.db_service)

        logger.info("✅ Service manager initialized successfully")

    def get_database_service(self) -> DatabaseService:
        """Get database service instance"""
        return self.db_service

    def get_model_service(self) -> ModelService:
        """Get model service instance"""
        return self.model_service

    def get_provider_service(self) -> ProviderService:
        """Get provider service instance"""
        return self.provider_service

    def get_model_provider_service(self) -> ModelProviderService:
        """Get model-provider service instance"""
        return self.model_provider_service

    def get_health_check_service(self) -> HealthCheckService:
        """Get health check service instance"""
        return self.health_check_service

    def health_check(self) -> dict:
        """Perform health check on all services"""
        health_status = {
            "database": "healthy",
            "model_service": "healthy",
            "provider_service": "healthy",
            "model_provider_service": "healthy",
            "health_check_service": "healthy",
            "overall": "healthy",
        }

        try:
            # Test database connection
            with self.db_service.get_session() as session:
                session.execute("SELECT 1")
        except Exception as e:
            health_status["database"] = "unhealthy"
            health_status["overall"] = "unhealthy"
            logger.error(f"Database health check failed: {e}")

        # Test service methods
        try:
            self.model_service.get_all_models()
        except Exception as e:
            health_status["model_service"] = "unhealthy"
            health_status["overall"] = "unhealthy"
            logger.error(f"Model service health check failed: {e}")

        try:
            self.provider_service.get_all_providers()
        except Exception as e:
            health_status["provider_service"] = "unhealthy"
            health_status["overall"] = "unhealthy"
            logger.error(f"Provider service health check failed: {e}")

        return health_status

    def get_service_info(self) -> dict:
        """Get information about all services"""
        return {
            "services": {
                "database_service": "Core database operations and connection management",
                "model_service": "Model management and configuration",
                "provider_service": "Provider management and health monitoring",
                "model_provider_service": "Model-provider association management",
                "health_check_service": "Health status synchronization and monitoring",
            },
            "total_services": 5,
            "status": "operational",
        }


# Global service manager instance
service_manager = ServiceManager()


# Convenience functions for backward compatibility
def get_db_service() -> DatabaseService:
    """Get database service (backward compatibility)"""
    return service_manager.get_database_service()


def get_model_service() -> ModelService:
    """Get model service (backward compatibility)"""
    return service_manager.get_model_service()


def get_provider_service() -> ProviderService:
    """Get provider service (backward compatibility)"""
    return service_manager.get_provider_service()


def get_model_provider_service() -> ModelProviderService:
    """Get model-provider service (backward compatibility)"""
    return service_manager.get_model_provider_service()


def get_health_check_service() -> HealthCheckService:
    """Get health check service (backward compatibility)"""
    return service_manager.get_health_check_service()
