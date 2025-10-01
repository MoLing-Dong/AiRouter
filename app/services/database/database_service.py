from sqlmodel import create_engine, Session, select
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Optional, Any
from datetime import datetime
import time
from app.models import (
    LLMModel,
    LLMProvider,
    LLMModelProvider,
    LLMModelParam,
    LLMProviderApiKey,
    LLMModelCreate,
    LLMProviderCreate,
    LLMModelProviderCreate,
    LLMModelProviderUpdate,
    LLMModelParamCreate,
    LLMProviderApiKeyCreate,
    HealthStatusEnum,
    QueryBuilder,
)
from config.settings import settings
from app.utils.logging_config import get_factory_logger
from .transaction_manager import DatabaseTransactionManager

# Get logger
logger = get_factory_logger()


class DatabaseService:
    """Core database service for connection and basic operations"""

    def __init__(self):
        # PostgreSQL database - SQLModel compatible
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=getattr(settings, "DB_POOL_SIZE", 10),
            max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 20),
            pool_timeout=getattr(settings, "DB_POOL_TIMEOUT", 30),
            pool_recycle=getattr(settings, "DB_POOL_RECYCLE", 3600),
            echo=False,  # 关闭数据库查询日志
        )
        # SQLModel uses Session directly, but keep SessionLocal for compatibility
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Initialize transaction manager
        self.tx_manager = DatabaseTransactionManager(self.SessionLocal)

    def close(self) -> None:
        """Close database engine and dispose connection pool"""
        try:
            if self.engine:
                self.engine.dispose()
        except Exception:
            # best effort close; avoid raising during shutdown
            pass

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()

    # ==================== Core Model Operations ====================

    def get_all_models(self, is_enabled: Optional[bool] = None) -> List[Any]:
        """Get all models from database with optional filtering"""
        try:
            with self.get_session() as session:
                query = session.query(LLMModel)

                if is_enabled is not None:
                    query = query.filter(LLMModel.is_enabled == is_enabled)

                # 添加排序和限制，避免返回过多数据
                models = query.order_by(LLMModel.name).all()

                return models
        except Exception as e:
            logger.warning(f"Failed to get all models: {e}")
            return []

    def get_model_by_name(
        self, model_name: str, is_enabled: bool = None
    ) -> Optional[LLMModel]:
        """Get model by name"""
        with self.get_session() as session:
            query = session.query(LLMModel).filter(LLMModel.name == model_name)
            if is_enabled is not None:
                query = query.filter(LLMModel.is_enabled == is_enabled)
            return query.first()

    def create_model(self, model_data: LLMModelCreate) -> LLMModel:
        """Create model with optional provider and capabilities association"""

        def _create_model_operation(session: Session):
            # Extract provider association data
            provider_id = getattr(model_data, "provider_id", None)
            provider_weight = getattr(model_data, "provider_weight", 10)
            is_provider_preferred = getattr(model_data, "is_provider_preferred", False)

            # Extract capabilities association data
            capability_ids = getattr(model_data, "capability_ids", None)

            # Validate provider if specified
            if provider_id:
                provider = self.tx_manager.validate_entity_exists(
                    session, LLMProvider, provider_id, "Provider"
                )
                self.tx_manager.validate_entity_enabled(provider, "Provider")

            # Validate capabilities if specified
            if capability_ids:
                from app.models import Capability

                for cap_id in capability_ids:
                    capability = (
                        session.query(Capability)
                        .filter_by(capability_id=cap_id)
                        .first()
                    )
                    if not capability:
                        raise ValueError(f"Capability not found: ID {cap_id}")

            # Create model (excluding provider and capability fields)
            model_dict = model_data.dict()
            model_dict.pop("provider_id", None)
            model_dict.pop("provider_weight", None)
            model_dict.pop("is_provider_preferred", None)
            model_dict.pop("capability_ids", None)

            # Check if model name already exists
            self.tx_manager.check_unique_constraint(
                session, LLMModel, {"name": model_dict["name"]}, "Model"
            )

            # Create and add model
            model = LLMModel(**model_dict)
            session.add(model)

            # Flush to get the model ID without committing
            session.flush()

            # Verify model was created successfully
            if not model.id:
                raise RuntimeError("Failed to create model - no ID generated")

            # Create model-provider association if provider_id is provided
            if provider_id:
                from app.models.llm_model_provider import LLMModelProvider

                # Check if association already exists
                self.tx_manager.check_unique_constraint(
                    session,
                    LLMModelProvider,
                    {"llm_id": model.id, "provider_id": provider_id},
                    "Model-Provider association",
                )

                # Create model-provider association
                model_provider = LLMModelProvider(
                    llm_id=model.id,
                    provider_id=provider_id,
                    weight=provider_weight,
                    is_preferred=is_provider_preferred,
                    is_enabled=True,
                )
                session.add(model_provider)

            # Create model-capability associations if capability_ids are provided
            if capability_ids:
                from app.models import LLMModelCapability

                for cap_id in capability_ids:
                    # Check if association already exists
                    existing = (
                        session.query(LLMModelCapability)
                        .filter_by(model_id=model.id, capability_id=cap_id)
                        .first()
                    )

                    if not existing:
                        # Create model-capability association
                        model_capability = LLMModelCapability(
                            model_id=model.id, capability_id=cap_id
                        )
                        session.add(model_capability)

            # Refresh model to get all attributes
            session.refresh(model)

            # Expunge the model from session so it can be used after session closes
            session.expunge(model)

            return model

        # Execute in transaction with retry mechanism
        try:
            logger.info(f"🔄 Starting model creation process for '{model_data.name}'")
            logger.debug(f"   📋 Model data: {model_data.dict()}")

            model = self.tx_manager.execute_with_retry(
                _create_model_operation,
                max_retries=2,
                description=f"Create model '{model_data.name}' with provider association",
            )

            # Log success details
            provider_info = ""
            if getattr(model_data, "provider_id", None):
                provider_info = f" with provider association (ID: {getattr(model_data, 'provider_id', None)})"
                logger.info(
                    f"✅ Successfully created model '{model.name}' (ID: {model.id}){provider_info}"
                )
                logger.debug(
                    f"   📍 Model details: name='{model.name}', type='{model.llm_type.value if hasattr(model.llm_type, 'value') else model.llm_type}', enabled={model.is_enabled}"
                )
                logger.debug(
                    f"   🔗 Provider association: provider_id={getattr(model_data, 'provider_id')}, weight={getattr(model_data, 'provider_weight', 10)}, preferred={getattr(model_data, 'is_provider_preferred', False)}"
                )
            else:
                logger.info(
                    f"✅ Successfully created model '{model.name}' (ID: {model.id}) without provider association"
                )
                logger.debug(
                    f"   📍 Model details: name='{model.name}', type='{model.llm_type.value if hasattr(model.llm_type, 'value') else model.llm_type}', enabled={model.is_enabled}"
                )

            return model

        except Exception as e:
            logger.error(f"❌ Failed to create model '{model_data.name}'")
            logger.error(f"   🚨 Error type: {type(e).__name__}")
            logger.error(f"   💬 Error message: {str(e)}")
            logger.error(f"   📋 Model data: {model_data.dict()}")

            # 记录详细的错误信息
            import traceback

            logger.error(f"   📚 Stack trace:\n{traceback.format_exc()}")

            raise

    def update_model_enabled_status(self, model_name: str, enabled: bool) -> bool:
        """Update model enabled status"""
        with self.get_session() as session:
            model = session.query(LLMModel).filter(LLMModel.name == model_name).first()
            if model:
                model.is_enabled = enabled
                session.commit()
                return True
            return False

    def get_model_updated_timestamp(self, model_name: str) -> Optional[float]:
        """Get model updated timestamp for version checking"""
        try:
            model = self.get_model_by_name(model_name, is_enabled=True)
            if model and model.updated_at:
                # Convert datetime to timestamp
                return model.updated_at.timestamp()
            return None
        except Exception as e:
            logger.info(f"Failed to get model timestamp for {model_name}: {e}")
            return None

    def get_all_models_capabilities_batch(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get capabilities for multiple models in batch (performance optimization)"""
        try:
            with self.get_session() as session:
                # 批量查询所有模型的capabilities - 使用单次JOIN查询
                from app.models import LLMModelCapability, Capability

                # 单次JOIN查询，避免N+1问题
                capabilities = (
                    session.query(
                        LLMModelCapability.model_id,
                        LLMModelCapability.capability_id,
                        Capability.capability_name,
                        Capability.description,
                    )
                    .join(
                        Capability,
                        LLMModelCapability.capability_id == Capability.capability_id,
                    )
                    .filter(
                        LLMModelCapability.model_id.in_(model_ids),
                    )
                    .all()
                )

                # 按模型ID分组
                result = {}
                for cap in capabilities:
                    if cap.model_id not in result:
                        result[cap.model_id] = []
                    result[cap.model_id].append(
                        {
                            "capability_id": cap.capability_id,
                            "capability_name": cap.capability_name,
                            "description": cap.description,
                        }
                    )

                return result
        except Exception as e:
            logger.warning(f"Failed to get batch capabilities: {e}")
            return {}

    def get_all_models_params_batch(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get parameters for multiple models in batch (performance optimization)"""
        try:
            with self.get_session() as session:
                # 批量查询所有模型的parameters - 使用单次查询
                from app.models import LLMModelParam

                # 单次查询，避免N+1问题
                params = (
                    session.query(
                        LLMModelParam.llm_id,
                        LLMModelParam.param_key,
                        LLMModelParam.param_value,
                        LLMModelParam.is_enabled,
                    )
                    .filter(
                        LLMModelParam.llm_id.in_(model_ids),
                    )
                    .all()
                )

                # 按模型ID分组
                result = {}
                for param in params:
                    if param.llm_id not in result:
                        result[param.llm_id] = []
                    result[param.llm_id].append(
                        {
                            "key": param.param_key,
                            "value": param.param_value,
                            "enabled": param.is_enabled,
                        }
                    )

                return result
        except Exception as e:
            logger.warning(f"Failed to get batch parameters: {e}")
            return {}

    def get_all_models_providers_batch(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get providers for multiple models in batch (performance optimization)"""
        try:
            with self.get_session() as session:
                # 批量查询所有模型的providers - 使用单次JOIN查询
                from app.models.llm_model_provider import LLMModelProvider
                from app.models.llm_provider import LLMProvider

                # 单次JOIN查询，避免N+1问题
                providers = (
                    session.query(
                        LLMModelProvider.llm_id,
                        LLMModelProvider.provider_id,
                        LLMModelProvider.weight,
                        LLMModelProvider.priority,
                        LLMModelProvider.health_status,
                        LLMModelProvider.is_enabled,
                        LLMModelProvider.is_preferred,
                        LLMModelProvider.cost_per_1k_tokens,
                        LLMModelProvider.overall_score,
                        LLMProvider.name,
                        LLMProvider.provider_type,
                        LLMProvider.official_endpoint,
                    )
                    .join(LLMProvider, LLMModelProvider.provider_id == LLMProvider.id)
                    .filter(LLMModelProvider.llm_id.in_(model_ids))
                    .all()
                )

                # 按模型ID分组
                result = {}
                for prov in providers:
                    if prov.llm_id not in result:
                        result[prov.llm_id] = []
                    result[prov.llm_id].append(
                        {
                            "provider_id": prov.provider_id,
                            "name": prov.name,
                            "provider_type": prov.provider_type,
                            "base_url": prov.official_endpoint,
                            "weight": prov.weight,
                            "priority": prov.priority,
                            "health_status": prov.health_status,
                            "is_enabled": prov.is_enabled,
                            "is_preferred": prov.is_preferred,
                            "cost_per_1k_tokens": prov.cost_per_1k_tokens,
                            "overall_score": prov.overall_score,
                        }
                    )

                return result
        except Exception as e:
            logger.warning(f"Failed to get batch providers: {e}")
            return {}

    def get_all_models_providers_batch_optimized(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """Get providers for multiple models in batch using optimized SQL (best performance)"""
        try:
            with self.get_session() as session:
                from sqlalchemy import text

                # 使用原生SQL查询，避免ORM开销
                sql = text(
                    """
                    SELECT 
                        mp.llm_id,
                        mp.provider_id,
                        mp.weight,
                        mp.priority,
                        mp.health_status,
                        mp.is_enabled,
                        mp.is_preferred,
                        mp.cost_per_1k_tokens,
                        mp.overall_score,
                        p.name,
                        p.provider_type,
                        p.official_endpoint,
                    FROM llm_model_providers mp
                    JOIN llm_providers p ON mp.provider_id = p.id
                    WHERE mp.llm_id = ANY(:model_ids)
                    ORDER BY mp.llm_id, mp.priority DESC, mp.weight DESC
                """
                )

                result = session.execute(sql, {"model_ids": model_ids})

                # 按模型ID分组
                providers_by_model = {}
                for row in result:
                    if row.llm_id not in providers_by_model:
                        providers_by_model[row.llm_id] = []

                    providers_by_model[row.llm_id].append(
                        {
                            "provider_id": row.provider_id,
                            "name": row.name,
                            "provider_type": row.provider_type,
                            "base_url": row.official_endpoint,
                            "weight": row.weight,
                            "priority": row.priority,
                            "health_status": row.health_status,
                            "is_enabled": row.is_enabled,
                            "is_preferred": row.is_preferred,
                            "cost_per_1k_tokens": row.cost_per_1k_tokens,
                            "overall_score": row.overall_score,
                        }
                    )

                return providers_by_model

        except Exception as e:
            logger.warning(f"Failed to get optimized batch providers: {e}")
            return {}

    def get_model_capabilities(self, model_id: int) -> List[Dict[str, Any]]:
        """Get model capabilities by model ID"""
        try:
            from app.models import LLMModelCapability, Capability

            with self.get_session() as session:
                capabilities = (
                    session.query(Capability)
                    .join(LLMModelCapability)
                    .filter(LLMModelCapability.model_id == model_id)
                    .all()
                )

                return [
                    {
                        "capability_id": cap.capability_id,
                        "capability_name": cap.capability_name,
                        "description": cap.description,
                    }
                    for cap in capabilities
                ]
        except Exception as e:
            logger.info(f"Get model capabilities failed for model {model_id}: {e}")
            return []

    def get_all_capabilities(self) -> List[Dict[str, Any]]:
        """Get all available capabilities"""
        try:
            from app.models import Capability

            with self.get_session() as session:
                capabilities = session.query(Capability).all()

                return [
                    {
                        "capability_id": cap.capability_id,
                        "capability_name": cap.capability_name,
                        "description": cap.description,
                    }
                    for cap in capabilities
                ]
        except Exception as e:
            logger.info(f"Get all capabilities failed: {e}")
            return []

    def add_model_capability(self, model_id: int, capability_name: str) -> bool:
        """Add capability to model"""
        try:
            from app.models import LLMModelCapability, Capability

            with self.get_session() as session:
                # Check if capability exists
                capability = (
                    session.query(Capability)
                    .filter(Capability.capability_name == capability_name)
                    .first()
                )

                if not capability:
                    logger.info(f"Capability {capability_name} does not exist")
                    return False

                # Check if association already exists
                existing = (
                    session.query(LLMModelCapability)
                    .filter(
                        LLMModelCapability.model_id == model_id,
                        LLMModelCapability.capability_id == capability.capability_id,
                    )
                    .first()
                )

                if existing:
                    logger.info(
                        f"Model {model_id} already has capability {capability_name}"
                    )
                    return True  # Already exists, consider as success

                # Create new association
                model_capability = LLMModelCapability(
                    model_id=model_id, capability_id=capability.capability_id
                )

                session.add(model_capability)
                session.commit()

                logger.info(f"Added capability {capability_name} to model {model_id}")
                return True

        except Exception as e:
            logger.info(f"Add model capability failed: {e}")
            return False

    def remove_model_capability(self, model_id: int, capability_name: str) -> bool:
        """Remove capability from model"""
        try:
            from app.models import LLMModelCapability, Capability

            with self.get_session() as session:
                # Find capability
                capability = (
                    session.query(Capability)
                    .filter(Capability.capability_name == capability_name)
                    .first()
                )

                if not capability:
                    logger.info(f"Capability {capability_name} does not exist")
                    return False

                # Remove association
                result = (
                    session.query(LLMModelCapability)
                    .filter(
                        LLMModelCapability.model_id == model_id,
                        LLMModelCapability.capability_id == capability.capability_id,
                    )
                    .delete()
                )

                session.commit()

                if result > 0:
                    logger.info(
                        f"Removed capability {capability_name} from model {model_id}"
                    )
                    return True
                else:
                    logger.info(
                        f"Model {model_id} does not have capability {capability_name}"
                    )
                    return False

        except Exception as e:
            logger.info(f"Remove model capability failed: {e}")
            return False

    def get_model_config_from_db(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get model configuration from database"""
        model = self.get_model_by_name(model_name, is_enabled=True)
        if not model:
            return None

        # Get all providers of the model
        model_providers = self.get_model_providers(model.id, is_enabled=True)
        providers = []

        for mp in model_providers:
            provider = self.get_provider_by_id(mp.provider_id, is_enabled=True)
            if not provider:
                continue

            # Get best API key
            api_key_obj = self.get_best_api_key(provider.id)
            if not api_key_obj:
                logger.info(
                    f"Warning: Provider {provider.name} has no available API keys"
                )
                continue

            # Get provider parameters
            provider_params = self.get_model_params(
                model.id, provider.id, is_enabled=True
            )
            params = {}
            for param in provider_params:
                # Handle JSON-formatted parameter values
                if isinstance(param.param_value, dict):
                    params[param.param_key] = param.param_value
                else:
                    params[param.param_key] = param.param_value

            # Get general parameters
            general_params = self.get_model_params(model.id, None, is_enabled=True)
            for param in general_params:
                if param.param_key not in params:
                    if isinstance(param.param_value, dict):
                        params[param.param_key] = param.param_value
                    else:
                        params[param.param_key] = param.param_value

            # Build provider configuration
            provider_config = {
                "name": provider.name,
                "base_url": provider.official_endpoint,
                "api_key": api_key_obj.api_key,
                "model": model.name,  # Use model name
                "model_id": model.id,  # 添加模型ID
                "provider_id": provider.id,  # 添加提供商ID
                "weight": mp.weight,
                "max_tokens": int(params.get("max_tokens", 4096)),
                "temperature": float(params.get("temperature", 0.7)),
                "cost_per_1k_tokens": float(params.get("cost_per_1k_tokens", 0.0)),
                "timeout": int(params.get("timeout", 30)),
                "retry_count": int(params.get("retry_count", 3)),
                "enabled": mp.is_enabled,
                "is_preferred": mp.is_preferred,
                "api_key_name": api_key_obj.name,
                "api_key_weight": api_key_obj.weight,
            }

            providers.append(provider_config)

        # Build model configuration
        model_config = {
            "name": model.name,
            "providers": providers,
            "model_type": "chat",  # Default type
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "enabled": model.is_enabled,
            "priority": 0,
            "updated_at": (
                model.updated_at.timestamp() if model.updated_at else time.time()
            ),
        }

        return model_config

    def get_model_config_by_name(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get single model configuration by name (alias for get_model_config_from_db)"""
        return self.get_model_config_from_db(model_name)

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """Get all model configurations from database"""
        models = self.get_all_models(is_enabled=True)
        configs = {}

        for model in models:
            config = self.get_model_config_from_db(model.name)
            if config:
                configs[model.name] = config

        return configs

    def get_best_provider_for_model(self, model_name: str) -> Optional[LLMProvider]:
        """Get best provider for specified model"""
        model = self.get_model_by_name(model_name, is_enabled=True)
        if not model:
            return None

        # Get all providers of the model, sorted by overall score
        model_providers = self.get_model_providers(model.id, is_enabled=True)
        if not model_providers:
            return None

        # Sort by overall score, select the best
        best_model_provider = max(model_providers, key=lambda mp: mp.overall_score)
        return self.get_provider_by_id(best_model_provider.provider_id)

    def get_provider_health_status(self, provider_name: str) -> Dict[str, Any]:
        """Get provider health status"""
        provider = self.get_provider_by_name(provider_name)
        if not provider:
            return {}

        # Get the performance of the provider in all models
        with self.get_session() as session:
            model_providers = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.provider_id == provider.id)
                .all()
            )

        if not model_providers:
            return {}

        # Calculate overall health status
        total_score = sum(mp.overall_score for mp in model_providers)
        avg_score = total_score / len(model_providers)

        # Determine overall health status
        if avg_score >= 0.8:
            overall_health = "healthy"
        elif avg_score >= 0.5:
            overall_health = "degraded"
        else:
            overall_health = "unhealthy"

        return {
            "provider_name": provider.name,
            "overall_health": overall_health,
            "average_score": avg_score,
            "total_models": len(model_providers),
            "healthy_models": len(
                [mp for mp in model_providers if mp.health_status == "healthy"]
            ),
            "degraded_models": len(
                [mp for mp in model_providers if mp.health_status == "degraded"]
            ),
            "unhealthy_models": len(
                [mp for mp in model_providers if mp.health_status == "unhealthy"]
            ),
            "model_details": [
                {
                    "model_id": mp.llm_id,
                    "health_status": mp.health_status,
                    "overall_score": mp.overall_score,
                    "response_time_avg": mp.response_time_avg,
                    "success_rate": mp.success_rate,
                    "cost_per_1k_tokens": mp.cost_per_1k_tokens,
                }
                for mp in model_providers
            ],
        }

    def get_all_providers(self) -> List[Dict[str, Any]]:
        """Get all providers"""
        providers = self.get_all_providers(is_enabled=True)
        result = []
        for provider in providers:
            result.append({"provider": provider})
        return result

    def get_all_providers_with_health(self) -> List[Dict[str, Any]]:
        """Get all providers and their health status"""
        providers = self.get_all_providers(is_enabled=True)
        result = []

        for provider in providers:
            health_info = self.get_provider_health_status(provider.name)
            if health_info:
                result.append({"provider": provider, "health_info": health_info})

        # Sort by average score
        result.sort(key=lambda x: x["health_info"]["average_score"], reverse=True)
        return result

    def update_provider_health_status(
        self, provider_name: str, health_status: str
    ) -> bool:
        """Update provider health status (affects all related models)"""
        provider = self.get_provider_by_name(provider_name)
        if not provider:
            return False

        with self.get_session() as session:
            # Update the health status of the provider in all models
            model_providers = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.provider_id == provider.id)
                .all()
            )

            for mp in model_providers:
                mp.health_status = health_status
                mp.last_health_check = datetime.now()
                self._recalculate_scores(mp)

            session.commit()
            return True

    def get_provider_performance_stats(self, provider_name: str) -> Dict[str, Any]:
        """Get provider performance statistics"""
        provider = self.get_provider_by_name(provider_name)
        if not provider:
            return {}

        with self.get_session() as session:
            model_providers = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.provider_id == provider.id)
                .all()
            )

        if not model_providers:
            return {}

        # Calculate overall statistics
        total_requests = sum(mp.total_requests for mp in model_providers)
        total_successful = sum(mp.successful_requests for mp in model_providers)
        total_cost = sum(mp.total_cost for mp in model_providers)
        total_tokens = sum(mp.total_tokens_used for mp in model_providers)

        # Calculate average response time
        response_times = [
            mp.response_time_avg for mp in model_providers if mp.response_time_avg > 0
        ]
        avg_response_time = (
            sum(response_times) / len(response_times) if response_times else 0
        )

        # Calculate average success rate
        success_rates = [
            mp.success_rate for mp in model_providers if mp.success_rate > 0
        ]
        avg_success_rate = (
            sum(success_rates) / len(success_rates) if success_rates else 0
        )

        return {
            "provider_name": provider.name,
            "total_requests": total_requests,
            "total_successful_requests": total_successful,
            "total_failed_requests": total_requests - total_successful,
            "overall_success_rate": (
                total_successful / total_requests if total_requests > 0 else 0
            ),
            "average_response_time": avg_response_time,
            "average_success_rate": avg_success_rate,
            "total_cost": total_cost,
            "total_tokens_used": total_tokens,
            "cost_per_1k_tokens": (
                (total_cost / total_tokens * 1000) if total_tokens > 0 else 0
            ),
            "models_count": len(model_providers),
            "healthy_models": len(
                [mp for mp in model_providers if mp.health_status == "healthy"]
            ),
            "degraded_models": len(
                [mp for mp in model_providers if mp.health_status == "degraded"]
            ),
            "unhealthy_models": len(
                [mp for mp in model_providers if mp.health_status == "unhealthy"]
            ),
        }

    def get_provider_recommendations(
        self, model_name: str = None
    ) -> List[Dict[str, Any]]:
        """Get provider recommendations"""
        if model_name:
            # Recommend providers for specific models
            model = self.get_model_by_name(model_name, is_enabled=True)
            if not model:
                return []

            model_providers = self.get_model_providers(model.id, is_enabled=True)
            recommendations = []

            for mp in sorted(
                model_providers, key=lambda x: x.overall_score, reverse=True
            ):
                provider = self.get_provider_by_id(mp.provider_id)
                if provider:
                    recommendations.append(
                        {
                            "provider": provider,
                            "score": mp.overall_score,
                            "health_status": mp.health_status,
                            "response_time": mp.response_time_avg,
                            "success_rate": mp.success_rate,
                            "cost_per_1k_tokens": mp.cost_per_1k_tokens,
                            "reason": self._get_recommendation_reason(mp),
                        }
                    )

            return recommendations
        else:
            # Global provider recommendations
            providers_with_health = self.get_all_providers_with_health()
            return providers_with_health[:10]

    def _get_recommendation_reason(self, model_provider: LLMModelProvider) -> str:
        """Get recommendation reasons"""
        reasons = []

        if model_provider.health_status == "healthy":
            reasons.append("Healthy status")

        if model_provider.response_time_avg < 2.0:
            reasons.append("Fast response time")

        if model_provider.success_rate > 0.95:
            reasons.append("High success rate")

        if model_provider.cost_per_1k_tokens < 0.01:
            reasons.append("Low cost")

        if model_provider.is_preferred:
            reasons.append("Preferred provider")

        return "、".join(reasons) if reasons else "High overall score"

    def get_healthy_model_providers(self, model_id: int) -> List[LLMModelProvider]:
        """Get healthy model-provider associations"""
        with self.get_session() as session:
            return (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.is_enabled == True,
                    LLMModelProvider.health_status == HealthStatusEnum.HEALTHY.value,
                )
                .order_by(LLMModelProvider.overall_score.desc())
                .all()
            )

    def get_best_model_provider(self, model_id: int) -> Optional[LLMModelProvider]:
        """Get best model-provider association (based on overall score)"""
        with self.get_session() as session:
            return (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.is_enabled == True,
                    LLMModelProvider.health_status.in_(
                        [
                            HealthStatusEnum.HEALTHY.value,
                            HealthStatusEnum.DEGRADED.value,
                        ]
                    ),
                )
                .order_by(LLMModelProvider.overall_score.desc())
                .first()
            )

    def update_provider_weight(
        self, model_name: str, provider_name: str, weight: int
    ) -> bool:
        """Update provider weight"""
        with self.get_session() as session:
            model = session.query(LLMModel).filter(LLMModel.name == model_name).first()
            if not model:
                return False

            provider = (
                session.query(LLMProvider)
                .filter(LLMProvider.name == provider_name)
                .first()
            )
            if not provider:
                return False

            model_provider = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model.id,
                    LLMModelProvider.provider_id == provider.id,
                )
                .first()
            )

            if model_provider:
                model_provider.weight = weight
                session.commit()
                return True
            return False

    def update_model_provider_strategy(
        self,
        model_name: str,
        provider_name: str,
        strategy: str,
        strategy_config: Dict[str, Any] = None,
        priority: int = None,
    ) -> bool:
        """Update model-provider load balancing strategy"""
        try:
            with self.get_session() as session:
                # Get model and provider
                model = self.get_model_by_name(model_name)
                provider = self.get_provider_by_name(provider_name)

                if not model or not provider:
                    return False

                # Get model-provider association
                model_provider = (
                    session.query(LLMModelProvider)
                    .filter(
                        LLMModelProvider.llm_id == model.id,
                        LLMModelProvider.provider_id == provider.id,
                    )
                    .first()
                )

                if not model_provider:
                    return False

                # Update strategy configuration
                model_provider.load_balancing_strategy = strategy
                if strategy_config is not None:
                    model_provider.strategy_config = strategy_config
                if priority is not None:
                    model_provider.priority = priority

                session.commit()
                return True

        except Exception as e:
            logger.info(f"Update load balancing strategy failed: {e}")
            return False

    def get_model_provider_strategy(
        self, model_name: str, provider_name: str
    ) -> Optional[Dict[str, Any]]:
        """Get model-provider load balancing strategy"""
        try:
            model = self.get_model_by_name(model_name)
            provider = self.get_provider_by_name(provider_name)

            if not model or not provider:
                return None

            with self.get_session() as session:
                model_provider = (
                    session.query(LLMModelProvider)
                    .filter(
                        LLMModelProvider.llm_id == model.id,
                        LLMModelProvider.provider_id == provider.id,
                    )
                    .first()
                )

                if not model_provider:
                    return None

                return {
                    "strategy": model_provider.load_balancing_strategy,
                    "strategy_config": model_provider.strategy_config,
                    "priority": model_provider.priority,
                    "max_retries": model_provider.max_retries,
                    "retry_delay": model_provider.retry_delay,
                    "circuit_breaker_enabled": model_provider.circuit_breaker_enabled,
                    "circuit_breaker_threshold": model_provider.circuit_breaker_threshold,
                    "circuit_breaker_timeout": model_provider.circuit_breaker_timeout,
                }

        except Exception as e:
            logger.info(f"Get load balancing strategy failed: {e}")
            return None

    def get_model_strategies(self, model_name: str) -> List[Dict[str, Any]]:
        """Get all provider strategies of the model"""
        try:
            model = self.get_model_by_name(model_name, is_enabled=True)
            if not model:
                return []

            model_providers = self.get_model_providers(model.id, is_enabled=True)
            strategies = []

            for mp in model_providers:
                provider = self.get_provider_by_id(mp.provider_id)
                if provider:
                    strategies.append(
                        {
                            "provider_name": provider.name,
                            "strategy": mp.load_balancing_strategy,
                            "strategy_config": mp.strategy_config,
                            "priority": mp.priority,
                            "weight": mp.weight,
                            "is_preferred": mp.is_preferred,
                            "health_status": mp.health_status,
                            "overall_score": mp.overall_score,
                        }
                    )

            return strategies

        except Exception as e:
            logger.info(f"Get model strategies failed: {e}")
            return []

    def update_model_provider_circuit_breaker(
        self,
        model_name: str,
        provider_name: str,
        enabled: bool = None,
        threshold: int = None,
        timeout: int = None,
    ) -> bool:
        """Update model-provider circuit breaker configuration"""
        try:
            with self.get_session() as session:
                model = self.get_model_by_name(model_name)
                provider = self.get_provider_by_name(provider_name)

                if not model or not provider:
                    return False

                model_provider = (
                    session.query(LLMModelProvider)
                    .filter(
                        LLMModelProvider.llm_id == model.id,
                        LLMModelProvider.provider_id == provider.id,
                    )
                    .first()
                )

                if not model_provider:
                    return False

                if enabled is not None:
                    model_provider.circuit_breaker_enabled = enabled
                if threshold is not None:
                    model_provider.circuit_breaker_threshold = threshold
                if timeout is not None:
                    model_provider.circuit_breaker_timeout = timeout

                session.commit()
                return True

        except Exception as e:
            logger.info(f"Update circuit breaker configuration failed: {e}")
            return False

    def get_available_strategies(self) -> List[str]:
        """Get all available load balancing strategies"""
        from .load_balancing_strategies import LoadBalancingStrategy

        return [strategy.value for strategy in LoadBalancingStrategy]

    def get_strategy_statistics(self, model_name: str = None) -> Dict[str, Any]:
        """Get strategy usage statistics"""
        try:
            with self.get_session() as session:
                query = session.query(LLMModelProvider)

                if model_name:
                    model = self.get_model_by_name(model_name)
                    if model:
                        query = query.filter(LLMModelProvider.llm_id == model.id)

                model_providers = query.all()

                strategy_counts = {}
                for mp in model_providers:
                    strategy = mp.load_balancing_strategy
                    strategy_counts[strategy] = strategy_counts.get(strategy, 0) + 1

                return {
                    "total_model_providers": len(model_providers),
                    "strategy_distribution": strategy_counts,
                    "available_strategies": self.get_available_strategies(),
                }

        except Exception as e:
            logger.info(f"Get strategy statistics failed: {e}")
            return {}

    # ==================== Core Provider Operations ====================

    def get_provider_by_id(
        self, provider_id: int, is_enabled: bool = None
    ) -> Optional[LLMProvider]:
        """Get provider by ID"""
        with self.get_session() as session:
            query = session.query(LLMProvider).filter(LLMProvider.id == provider_id)

            if is_enabled is not None:
                query = query.filter(LLMProvider.is_enabled == is_enabled)

            return query.first()

    def get_provider_by_name(self, provider_name: str) -> Optional[LLMProvider]:
        """Get provider by name"""
        with self.get_session() as session:
            return (
                session.query(LLMProvider)
                .filter(LLMProvider.name == provider_name)
                .first()
            )

    def get_provider_by_name_and_type(
        self, provider_name: str, provider_type: str
    ) -> Optional[LLMProvider]:
        """Get provider by name and type"""
        with self.get_session() as session:
            return (
                session.query(LLMProvider)
                .filter(
                    LLMProvider.name == provider_name,
                    LLMProvider.provider_type == provider_type,
                )
                .first()
            )

    def get_all_providers(self, is_enabled: bool = None) -> List[LLMProvider]:
        """Get all providers"""
        with self.get_session() as session:
            query = session.query(LLMProvider)
            if is_enabled is not None:
                query = query.filter(LLMProvider.is_enabled == is_enabled)
            return query.all()

    def create_provider(self, provider_data: LLMProviderCreate) -> LLMProvider:
        """Create provider"""
        session = None
        try:
            session = self.get_session()

            # Check if provider already exists
            existing_provider = (
                session.query(LLMProvider)
                .filter(
                    LLMProvider.name == provider_data.name,
                    LLMProvider.provider_type == provider_data.provider_type,
                )
                .first()
            )

            if existing_provider:
                raise ValueError(
                    f"Provider with name '{provider_data.name}' and type '{provider_data.provider_type}' already exists"
                )

            # Create and add provider
            provider = LLMProvider(**provider_data.dict())
            session.add(provider)

            # Commit transaction
            session.commit()
            session.refresh(provider)

            logger.info(
                f"Successfully created provider '{provider.name}' (ID: {provider.id})"
            )
            return provider

        except Exception as e:
            # Rollback transaction on error
            if session:
                session.rollback()
                logger.error(
                    f"Failed to create provider: {str(e)}. Transaction rolled back."
                )

            # Re-raise the exception for proper error handling
            raise

        finally:
            # Always close session
            if session:
                session.close()

    # ==================== Core Model-Provider Operations ====================

    def get_model_providers(
        self, model_id: int, is_enabled: bool = None
    ) -> List[LLMModelProvider]:
        """Get all providers of the model"""
        with self.get_session() as session:
            query = session.query(LLMModelProvider).filter(
                LLMModelProvider.llm_id == model_id
            )
            if is_enabled is not None:
                query = query.filter(LLMModelProvider.is_enabled == is_enabled)
            return query.order_by(LLMModelProvider.weight.desc()).all()

    def get_model_provider_by_ids(
        self, model_id: int, provider_id: int, is_enabled: bool = None
    ) -> Optional[LLMModelProvider]:
        """Get model-provider association by model ID and provider ID"""
        with self.get_session() as session:
            query = session.query(LLMModelProvider).filter(
                LLMModelProvider.llm_id == model_id,
                LLMModelProvider.provider_id == provider_id,
            )
            if is_enabled is not None:
                query = query.filter(LLMModelProvider.is_enabled == is_enabled)
            return query.first()

    def create_model_provider(
        self, model_provider_data: LLMModelProviderCreate
    ) -> LLMModelProvider:
        """Create model-provider association"""
        session = None
        try:
            session = self.get_session()

            # Validate model exists
            model = (
                session.query(LLMModel)
                .filter(LLMModel.id == model_provider_data.llm_id)
                .first()
            )
            if not model:
                raise ValueError(
                    f"Model with ID {model_provider_data.llm_id} does not exist"
                )
            if not model.is_enabled:
                raise ValueError(
                    f"Model with ID {model_provider_data.llm_id} is disabled"
                )

            # Validate provider exists
            provider = (
                session.query(LLMProvider)
                .filter(LLMProvider.id == model_provider_data.provider_id)
                .first()
            )
            if not provider:
                raise ValueError(
                    f"Provider with ID {model_provider_data.provider_id} does not exist"
                )
            if not provider.is_enabled:
                raise ValueError(
                    f"Provider with ID {model_provider_data.provider_id} is disabled"
                )

            # Check if association already exists
            existing_association = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_provider_data.llm_id,
                    LLMModelProvider.provider_id == model_provider_data.provider_id,
                )
                .first()
            )

            if existing_association:
                raise ValueError(
                    f"Model-provider association already exists for model {model_provider_data.llm_id} and provider {model_provider_data.provider_id}"
                )

            # Create and add association
            model_provider = LLMModelProvider(**model_provider_data.dict())
            session.add(model_provider)

            # Commit transaction
            session.commit()
            session.refresh(model_provider)

            logger.info(
                f"Successfully created model-provider association: Model {model_provider_data.llm_id} -> Provider {model_provider_data.provider_id}"
            )
            return model_provider

        except Exception as e:
            # Rollback transaction on error
            if session:
                session.rollback()
                logger.error(
                    f"Failed to create model-provider association: {str(e)}. Transaction rolled back."
                )

            # Re-raise the exception for proper error handling
            raise

        finally:
            # Always close session
            if session:
                session.close()

    def update_model_provider(
        self, model_provider_id: int, model_provider_data: LLMModelProviderUpdate
    ) -> LLMModelProvider:
        """Update model-provider association"""
        with self.get_session() as session:
            # Find model-provider association to update
            model_provider = (
                session.query(LLMModelProvider)
                .filter(LLMModelProvider.id == model_provider_id)
                .first()
            )

            if not model_provider:
                raise ValueError(
                    f"Model-provider association does not exist: ID {model_provider_id}"
                )

            # Get update data
            update_data = model_provider_data.dict(exclude_unset=True)

            # If update contains llm_id or provider_id, need to check uniqueness constraint
            if "llm_id" in update_data or "provider_id" in update_data:
                new_llm_id = update_data.get("llm_id", model_provider.llm_id)
                new_provider_id = update_data.get(
                    "provider_id", model_provider.provider_id
                )

                # Check if new combination conflicts with other records (exclude current record)
                existing_conflict = (
                    session.query(LLMModelProvider)
                    .filter(
                        LLMModelProvider.llm_id == new_llm_id,
                        LLMModelProvider.provider_id == new_provider_id,
                        LLMModelProvider.id
                        != model_provider_id,  # Exclude current record
                    )
                    .first()
                )

                if existing_conflict:
                    raise ValueError(
                        f"Model-provider association already exists: Model ID {new_llm_id}, Provider ID {new_provider_id}"
                    )

            # Update all fields
            for field, value in update_data.items():
                setattr(model_provider, field, value)

            session.commit()
            session.refresh(model_provider)
            return model_provider

    # ==================== Core Model Parameter Operations ====================

    def get_model_params(
        self, model_id: int, provider_id: Optional[int] = None, is_enabled: bool = None
    ) -> List[LLMModelParam]:
        """Get model parameters"""
        with self.get_session() as session:
            query = session.query(LLMModelParam).filter(
                LLMModelParam.llm_id == model_id
            )

            if is_enabled is not None:
                query = query.filter(LLMModelParam.is_enabled == is_enabled)

            if provider_id is not None:
                query = query.filter(LLMModelParam.provider_id == provider_id)

            return query.all()

    def get_model_param_by_key(
        self,
        model_id: int,
        provider_id: Optional[int],
        param_key: str,
        is_enabled: bool = None,
    ) -> Optional[LLMModelParam]:
        """Get model parameters by model ID, provider ID and parameter key"""
        with self.get_session() as session:
            query = session.query(LLMModelParam).filter(
                LLMModelParam.llm_id == model_id,
                LLMModelParam.param_key == param_key,
            )

            if is_enabled is not None:
                query = query.filter(LLMModelParam.is_enabled == is_enabled)

            if provider_id is not None:
                query = query.filter(LLMModelParam.provider_id == provider_id)

            return query.first()

    def create_model_param(self, param_data: LLMModelParamCreate) -> LLMModelParam:
        """Create model parameters"""
        with self.get_session() as session:
            param = LLMModelParam(**param_data.dict())
            session.add(param)
            session.commit()
            session.refresh(param)
            return param

    # ==================== Core API Key Operations ====================

    def get_provider_api_keys(
        self, provider_id: int, is_enabled: bool = None
    ) -> List[LLMProviderApiKey]:
        """Get all API keys of the provider"""
        with self.get_session() as session:
            query = session.query(LLMProviderApiKey).filter(
                LLMProviderApiKey.provider_id == provider_id
            )
            if is_enabled is not None:
                query = query.filter(LLMProviderApiKey.is_enabled == is_enabled)
            return query.order_by(LLMProviderApiKey.weight.desc()).all()

    def get_best_api_key(self, provider_id: int) -> Optional[LLMProviderApiKey]:
        """Get best API key (based on weight and preference)"""
        api_keys = self.get_provider_api_keys(provider_id, is_enabled=True)
        if not api_keys:
            return None

        # Prefer preferred keys
        preferred_keys = [key for key in api_keys if key.is_preferred]
        if preferred_keys:
            # Sort by weight
            preferred_keys.sort(key=lambda x: x.weight, reverse=True)
            return preferred_keys[0]

        # If no preferred keys, sort by weight
        api_keys.sort(key=lambda x: x.weight, reverse=True)
        return api_keys[0]

    def create_provider_api_key(
        self, api_key_data: LLMProviderApiKeyCreate
    ) -> LLMProviderApiKey:
        """Create provider API key"""
        with self.get_session() as session:
            api_key = LLMProviderApiKey(**api_key_data.dict())
            session.add(api_key)
            session.commit()
            session.refresh(api_key)
            return api_key

    def update_api_key_usage(
        self, api_key_id: int, increment: bool = True, usage_count: int = None
    ) -> bool:
        """Update API key usage count"""
        with self.get_session() as session:
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == api_key_id)
                .first()
            )
            if api_key:
                if usage_count is not None:
                    api_key.usage_count = usage_count
                elif increment:
                    api_key.usage_count += 1
                else:
                    api_key.usage_count = max(0, api_key.usage_count - 1)
                session.commit()
                return True
            return False

    def get_api_key_for_provider(self, provider_name: str) -> Optional[str]:
        """Get API key for a specific provider by name"""
        with self.get_session() as session:
            # First get the provider by name
            provider = (
                session.query(LLMProvider)
                .filter(LLMProvider.name == provider_name)
                .first()
            )

            if not provider:
                return None

            # Get the best API key for this provider
            best_key = self.get_best_api_key(provider.id)
            return best_key.api_key if best_key else None

    # ==================== Health Status and Metrics Operations ====================

    def update_model_provider_health_status(
        self,
        model_id: int,
        provider_id: int,
        health_status: str,
        response_time: float = None,
        success: bool = None,
    ) -> bool:
        """Update model-provider health status"""
        with self.get_session() as session:
            model_provider = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

            if model_provider:
                model_provider.health_status = health_status
                model_provider.last_health_check = datetime.now()

                # Update performance metrics
                if response_time is not None:
                    self._update_response_time_stats(model_provider, response_time)

                if success is not None:
                    self._update_success_stats(model_provider, success)

                # Recalculate scores
                self._recalculate_scores(model_provider)

                session.commit()
                return True
            return False

    def update_model_provider_metrics(
        self,
        model_id: int,
        provider_id: int,
        response_time: float,
        success: bool,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> bool:
        """Update model-provider performance metrics"""
        with self.get_session() as session:
            model_provider = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

            if model_provider:
                # Update response time statistics
                self._update_response_time_stats(model_provider, response_time)

                # Update success rate statistics
                self._update_success_stats(model_provider, success)

                # Update cost statistics
                if cost > 0:
                    model_provider.total_cost += cost
                    model_provider.total_tokens_used += tokens_used
                    if tokens_used > 0:
                        model_provider.cost_per_1k_tokens = (
                            model_provider.total_cost / model_provider.total_tokens_used
                        ) * 1000

                # Recalculate scores
                self._recalculate_scores(model_provider)

                session.commit()
                return True
            return False

    def increment_failure_count(self, model_id: int, provider_id: int) -> bool:
        """Increment failure count"""
        with self.get_session() as session:
            model_provider = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

            if model_provider:
                model_provider.failure_count += 1
                model_provider.last_failure_time = datetime.now()

                # If failure count exceeds threshold and auto disable is enabled
                if (
                    model_provider.failure_count >= model_provider.max_failures
                    and model_provider.auto_disable_on_failure
                ):
                    model_provider.is_enabled = False
                    model_provider.health_status = HealthStatusEnum.UNHEALTHY.value

                session.commit()
                return True
            return False

    def reset_failure_count(self, model_id: int, provider_id: int) -> bool:
        """Reset failure count"""
        with self.get_session() as session:
            model_provider = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

            if model_provider:
                model_provider.failure_count = 0
                session.commit()
                return True
            return False

    def get_model_provider_stats(
        self, model_id: int, provider_id: int
    ) -> Dict[str, Any]:
        """Get model-provider statistics"""
        with self.get_session() as session:
            model_provider = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

            if model_provider:
                return {
                    "health_status": model_provider.health_status,
                    "response_time_avg": model_provider.response_time_avg,
                    "success_rate": model_provider.success_rate,
                    "total_requests": model_provider.total_requests,
                    "successful_requests": model_provider.successful_requests,
                    "failed_requests": model_provider.failed_requests,
                    "cost_per_1k_tokens": model_provider.cost_per_1k_tokens,
                    "total_cost": model_provider.total_cost,
                    "total_tokens_used": model_provider.total_tokens_used,
                    "health_score": model_provider.health_score,
                    "performance_score": model_provider.performance_score,
                    "cost_score": model_provider.cost_score,
                    "overall_score": model_provider.overall_score,
                    "failure_count": model_provider.failure_count,
                    "last_health_check": model_provider.last_health_check,
                    "last_failure_time": model_provider.last_failure_time,
                    "custom_config": model_provider.custom_config,
                    "model_metadata": model_provider.model_metadata,
                }
            return {}

    # ==================== Private Helper Methods ====================

    def _update_response_time_stats(
        self, model_provider: LLMModelProvider, response_time: float
    ):
        """Update response time statistics"""
        if model_provider.response_time_avg == 0:
            model_provider.response_time_avg = response_time
            model_provider.response_time_min = response_time
            model_provider.response_time_max = response_time
        else:
            # Use exponential moving average
            alpha = 0.1  # Smoothing factor
            model_provider.response_time_avg = (
                alpha * response_time + (1 - alpha) * model_provider.response_time_avg
            )
            model_provider.response_time_min = min(
                model_provider.response_time_min, response_time
            )
            model_provider.response_time_max = max(
                model_provider.response_time_max, response_time
            )

    def _update_success_stats(self, model_provider: LLMModelProvider, success: bool):
        """Update success rate statistics"""
        model_provider.total_requests += 1
        if success:
            model_provider.successful_requests += 1
        else:
            model_provider.failed_requests += 1

        # Calculate success rate
        if model_provider.total_requests > 0:
            model_provider.success_rate = (
                model_provider.successful_requests / model_provider.total_requests
            )

    def _recalculate_scores(self, model_provider: LLMModelProvider):
        """Recalculate scores"""
        # Health score
        if model_provider.health_status == HealthStatusEnum.HEALTHY.value:
            model_provider.health_score = 1.0
        elif model_provider.health_status == HealthStatusEnum.DEGRADED.value:
            model_provider.health_score = 0.5
        else:
            model_provider.health_score = 0.1

        # Performance score (based on response time and success rate)
        response_time_score = max(
            0, 1 - model_provider.response_time_avg / 10
        )  # 10 seconds linear decrease
        performance_score = (
            response_time_score * 0.5 + model_provider.success_rate * 0.5
        )
        model_provider.performance_score = min(1.0, max(0.0, performance_score))

        # Cost score (cheaper is better)
        cost_score = max(
            0, 1 - model_provider.cost_per_1k_tokens / 0.1
        )  # 0.1$/1K tokens linear decrease
        model_provider.cost_score = min(1.0, max(0.0, cost_score))

        # Overall score (weighted average)
        model_provider.overall_score = (
            model_provider.health_score * 0.4
            + model_provider.performance_score * 0.4
            + model_provider.cost_score * 0.2
        )


class LazyDatabaseService:
    """Lazy-initialized proxy for DatabaseService to avoid import-time side effects."""

    _instance: Optional[DatabaseService] = None

    def _ensure(self) -> DatabaseService:
        if self._instance is None:
            self._instance = DatabaseService()
        return self._instance

    def __getattr__(self, item):
        service = self._ensure()
        return getattr(service, item)

    def close(self) -> None:
        if self._instance is not None:
            self._instance.close()


# Global lazy database service instance
db_service = LazyDatabaseService()
