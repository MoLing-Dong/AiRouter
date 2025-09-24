"""
Service Factory
统一管理所有服务的实例化和依赖注入
"""

from app.services.database.transaction_manager import DatabaseTransactionManager
# 注释掉已删除的repositories和business导入
# from app.services.repositories.model_repository import ModelRepository
# from app.services.repositories.provider_repository import ProviderRepository
# from app.services.repositories.model_provider_repository import ModelProviderRepository
# from app.services.repositories.api_key_repository import ApiKeyRepository
# from app.services.business.model_service import ModelService
# from app.services.business.provider_service import ProviderService
# from app.services.business.model_provider_service import ModelProviderService
# from app.services.business.api_key_service import ApiKeyService

# 使用现有的服务
from .model_service import ModelService
from .provider_service import ProviderService
from .model_provider_service import ModelProviderService
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ServiceFactory:
    """Factory for creating and managing service instances"""

    def __init__(self, session_factory):
        self.session_factory = session_factory
        self._transaction_manager = None
        self._repositories = {}
        self._services = {}

        logger.info("🏭 Initializing Service Factory")
        self._initialize_services()

    def _initialize_services(self):
        """Initialize all services and their dependencies"""
        logger.debug("   🔧 Setting up transaction manager")
        self._transaction_manager = DatabaseTransactionManager(self.session_factory)

        logger.debug("   🔧 Setting up repositories")
        self._setup_repositories()

        logger.debug("   🔧 Setting up business services")
        self._setup_business_services()

        logger.info("✅ Service Factory initialization completed")

    def _setup_repositories(self):
        """Setup all repository instances - simplified"""
        # 使用数据库服务替代repositories
        from .database.database_service import DatabaseService
        self._db_service = DatabaseService()
        logger.debug("   📚 Database service initialized")

    def _setup_business_services(self):
        """Setup all business service instances - simplified"""
        # 使用数据库服务初始化现有服务
        self._services["model"] = ModelService(self._db_service)
        self._services["provider"] = ProviderService(self._db_service)
        self._services["model_provider"] = ModelProviderService(self._db_service)

        logger.debug(f"   🚀 Created {len(self._services)} business services")

    @property
    def transaction_manager(self) -> DatabaseTransactionManager:
        """Get transaction manager instance"""
        return self._transaction_manager

    def get_model_service(self) -> ModelService:
        """Get model service instance"""
        return self._services["model"]

    def get_provider_service(self) -> ProviderService:
        """Get provider service instance"""
        return self._services["provider"]

    def get_model_provider_service(self) -> ModelProviderService:
        """Get model-provider service instance"""
        return self._services["model_provider"]

    # def get_api_key_service(self) -> ApiKeyService:
    #     """Get API key service instance"""
    #     return self._services["api_key"]

    def get_repository(self, name: str):
        """Get repository by name"""
        if name not in self._repositories:
            raise ValueError(f"Repository '{name}' not found")
        return self._repositories[name]

    def get_service(self, name: str):
        """Get service by name"""
        if name not in self._services:
            raise ValueError(f"Service '{name}' not found")
        return self._services[name]

    def get_all_services(self) -> dict:
        """Get all services"""
        return self._services.copy()

    def get_all_repositories(self) -> dict:
        """Get all repositories"""
        return self._repositories.copy()

    def health_check(self) -> dict:
        """Perform health check on all services"""
        health_status = {
            "status": "healthy",
            "services": {},
            "repositories": {},
            "transaction_manager": "healthy",
        }

        # Check repositories
        for name, repo in self._repositories.items():
            try:
                # Simple health check - try to get count
                count = repo.count()
                health_status["repositories"][name] = {
                    "status": "healthy",
                    "count": count,
                }
            except Exception as e:
                health_status["repositories"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["status"] = "unhealthy"

        # Check services
        for name, service in self._services.items():
            try:
                # Simple health check - try to access service attributes
                if hasattr(service, "get_all") and callable(service.get_all):
                    health_status["services"][name] = {
                        "status": "healthy",
                        "type": type(service).__name__,
                    }
                else:
                    health_status["services"][name] = {
                        "status": "healthy",
                        "type": type(service).__name__,
                    }
            except Exception as e:
                health_status["services"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                }
                health_status["status"] = "unhealthy"

        logger.info(f"🏥 Health check completed: {health_status['status']}")
        return health_status

    def reset_services(self):
        """Reset all services (useful for testing)"""
        logger.info("🔄 Resetting all services")
        self._initialize_services()

    def get_service_info(self) -> dict:
        """Get information about all services"""
        info = {
            "transaction_manager": {
                "type": type(self._transaction_manager).__name__,
                "session_factory": str(self.session_factory),
            },
            "repositories": {},
            "services": {},
        }

        for name, repo in self._repositories.items():
            info["repositories"][name] = {
                "type": type(repo).__name__,
                "entity_class": repo.entity_class.__name__,
            }

        for name, service in self._services.items():
            info["services"][name] = {
                "type": type(service).__name__,
                "dependencies": [
                    dep.__class__.__name__
                    for dep in service.__dict__.values()
                    if hasattr(dep, "__class__")
                ],
            }

        return info
