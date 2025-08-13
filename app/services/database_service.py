from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Optional, Any
from datetime import datetime
from ..models import (
    Base,
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
)
from ..models.llm_model_provider import HealthStatusEnum
from config.settings import settings
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class DatabaseService:
    """Database service"""

    def __init__(self):
        # PostgreSQL database
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.DEBUG,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create tables
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """Get database session"""
        return self.SessionLocal()

    def get_all_models(self, is_enabled: bool = None) -> List[LLMModel]:
        """Get all models

        Args:
            is_enabled: Whether to enable, None means ignore enable status
        """
        with self.get_session() as session:
            query = session.query(LLMModel)
            if is_enabled is not None:
                query = query.filter(LLMModel.is_enabled == is_enabled)
            return query.all()

    def get_model_by_name(
        self, model_name: str, is_enabled: bool = None
    ) -> Optional[LLMModel]:
        """Get model by name

        Args:
            model_name: Model name
            is_enabled: Whether to enable, None means ignore enable status
        """
        with self.get_session() as session:
            query = session.query(LLMModel).filter(LLMModel.name == model_name)
            if is_enabled is not None:
                query = query.filter(LLMModel.is_enabled == is_enabled)
            return query.first()

    def get_model_providers(
        self, model_id: int, is_enabled: bool = None
    ) -> List[LLMModelProvider]:
        """Get all providers of the model

        Args:
            model_id: Model ID
            is_enabled: Whether to enable, None means ignore enable status
        """
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
        """Get model-provider association by model ID and provider ID

        Args:
            model_id: Model ID
            provider_id: Provider ID
            is_enabled: Whether to enable, None means ignore enable status
        """
        with self.get_session() as session:
            query = session.query(LLMModelProvider).filter(
                LLMModelProvider.llm_id == model_id,
                LLMModelProvider.provider_id == provider_id,
            )
            if is_enabled is not None:
                query = query.filter(LLMModelProvider.is_enabled == is_enabled)
            return query.first()

    def get_model_params(
        self, model_id: int, provider_id: Optional[int] = None, is_enabled: bool = None
    ) -> List[LLMModelParam]:
        """Get model parameters

        Args:
            model_id: Model ID
            provider_id: Provider ID, None means get general parameters
            is_enabled: Whether to enable, None means ignore enable status
        """
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
        """Get model parameters by model ID, provider ID and parameter key

        Args:
            model_id: Model ID
            provider_id: Provider ID, None means get general parameters
            param_key: Parameter key
            is_enabled: Whether to enable, None means ignore enable status
        """
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

    def get_provider_by_id(
        self, provider_id: int, is_enabled: bool = None
    ) -> Optional[LLMProvider]:
        """Get provider by ID

        Args:
            provider_id: Provider ID
            is_enabled: Whether to enable, None means ignore enable status
        """
        with self.get_session() as session:
            query = session.query(LLMProvider).filter(LLMProvider.id == provider_id)

            if is_enabled is not None:
                query = query.filter(LLMProvider.is_enabled == is_enabled)

            return query.first()

    def get_provider_api_keys(
        self, provider_id: int, is_enabled: bool = None
    ) -> List[LLMProviderApiKey]:
        """Get all API keys of the provider

        Args:
            provider_id: Provider ID
            is_enabled: Whether to enable, None means ignore enable status
        """
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

    def create_model(self, model_data: LLMModelCreate) -> LLMModel:
        """Create model"""
        with self.get_session() as session:
            model = LLMModel(**model_data.dict())
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def create_provider(self, provider_data: LLMProviderCreate) -> LLMProvider:
        """Create provider"""
        with self.get_session() as session:
            provider = LLMProvider(**provider_data.dict())
            session.add(provider)
            session.commit()
            session.refresh(provider)
            return provider

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

    def create_model_provider(
        self, model_provider_data: LLMModelProviderCreate
    ) -> LLMModelProvider:
        """Create model-provider association"""
        with self.get_session() as session:
            model_provider = LLMModelProvider(**model_provider_data.dict())
            session.add(model_provider)
            session.commit()
            session.refresh(model_provider)
            return model_provider

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
                raise ValueError(f"Model-provider association does not exist: ID {model_provider_id}")

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
                        LLMModelProvider.id != model_provider_id,  # Exclude current record
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

    def create_model_param(self, param_data: LLMModelParamCreate) -> LLMModelParam:
        """Create model parameters"""
        with self.get_session() as session:
            param = LLMModelParam(**param_data.dict())
            session.add(param)
            session.commit()
            session.refresh(param)
            return param

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
                logger.info(f"Warning: Provider {provider.name} has no available API keys")
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
                "base_url": provider.official_endpoint or provider.third_party_endpoint,
                "api_key": api_key_obj.api_key,
                "model": model.name,  # Use model name
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
        }

        return model_config

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """Get all model configurations from database"""
        models = self.get_all_models(is_enabled=True)
        configs = {}

        for model in models:
            config = self.get_model_config_from_db(model.name)
            if config:
                configs[model.name] = config

        return configs

    def update_model_enabled_status(self, model_name: str, enabled: bool) -> bool:
        """Update model enabled status"""
        with self.get_session() as session:
            model = session.query(LLMModel).filter(LLMModel.name == model_name).first()
            if model:
                model.is_enabled = enabled
                session.commit()
                return True
            return False

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
                    LLMModelprovider.id == provider.id,
                )
                .first()
            )

            if model_provider:
                model_provider.weight = weight
                session.commit()
                return True
            return False

    def get_all_providers(self, is_enabled: bool = None) -> List[LLMProvider]:
        """Get all providers

        Args:
            is_enabled: Whether to enable, None means ignore enable status
        """
        with self.get_session() as session:
            query = session.query(LLMProvider)
            if is_enabled is not None:
                query = query.filter(LLMProvider.is_enabled == is_enabled)
            return query.all()

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

    def update_api_key_usage(self, apikey_id: int, usage_count: int = None) -> bool:
        """Update API key usage count"""
        with self.get_session() as session:
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == apikey_id)
                .first()
            )
            if api_key:
                if usage_count is not None:
                    api_key.usage_count = usage_count
                else:
                    api_key.usage_count += 1
                session.commit()
                return True
            return False

    # ==================== Methods based on provider ====================

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

    def get_top_providers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top providers"""
        providers_with_health = self.get_all_providers_with_health()
        return providers_with_health[:limit]

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
            return self.get_top_providers(10)

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

    # ==================== Health status and evaluation related methods ====================

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

    # ==================== Private helper methods ====================

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


# Global database service instance
db_service = DatabaseService()
