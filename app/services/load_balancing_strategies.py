import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from ..core.adapters import ChatRequest, ChatResponse
from ..core.adapters.base import BaseAdapter, HealthStatus
from .database_service import db_service
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy enumeration"""

    AUTO = "auto"  # Auto select best provider
    SPECIFIED_PROVIDER = "specified_provider"  # Specify provider
    FALLBACK = "fallback"  # Fallback
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # Weighted round robin
    LEAST_CONNECTIONS = "least_connections"  # Least connections
    RESPONSE_TIME = "response_time"  # Response time priority
    COST_OPTIMIZED = "cost_optimized"  # Cost optimized
    HYBRID = "hybrid"  # Hybrid strategy


@dataclass
class ProviderInfo:
    """Provider information"""

    name: str
    adapter: BaseAdapter
    weight: int
    priority: int
    health_status: str
    response_time_avg: float
    success_rate: float
    cost_per_1k_tokens: float
    overall_score: float
    current_connections: int = 0
    last_used_time: float = 0.0
    hybrid_score: float = 0.0  # Hybrid strategy score


class LoadBalancingStrategyManager:
    """Load balancing strategy manager"""

    def __init__(self):
        self.provider_connections: Dict[str, int] = (
            {}
        )  # Record current connection count of each provider
        self.provider_last_used: Dict[str, float] = (
            {}
        )  # Record last used time of each provider
        self.round_robin_counters: Dict[str, int] = {}  # Round robin counter

    async def execute_strategy(
        self,
        request: ChatRequest,
        model_providers: List[Any],
        strategy: str,
        strategy_config: Dict[str, Any] = None,
    ) -> ChatResponse:
        """Execute specified load balancing strategy"""

        if strategy_config is None:
            strategy_config = {}

        # Build provider information list
        providers = await self._build_provider_info_list(request.model, model_providers)

        if not providers:
            raise Exception(f"Model {request.model} has no available providers")

        # Select provider based on strategy
        match strategy:
            case LoadBalancingStrategy.AUTO:
                return await self._execute_auto_strategy(request, providers)
            case LoadBalancingStrategy.SPECIFIED_PROVIDER:
                return await self._execute_specified_provider_strategy(
                    request, providers, strategy_config
                )
            case LoadBalancingStrategy.FALLBACK:
                return await self._execute_fallback_strategy(
                    request, providers, strategy_config
                )
            case LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN:
                return await self._execute_weighted_round_robin_strategy(
                    request, providers, strategy_config
                )
            case LoadBalancingStrategy.LEAST_CONNECTIONS:
                return await self._execute_least_connections_strategy(
                    request, providers, strategy_config
                )
            case LoadBalancingStrategy.RESPONSE_TIME:
                return await self._execute_response_time_strategy(
                    request, providers, strategy_config
                )
            case LoadBalancingStrategy.COST_OPTIMIZED:
                return await self._execute_cost_optimized_strategy(
                    request, providers, strategy_config
                )
            case LoadBalancingStrategy.HYBRID:
                return await self._execute_hybrid_strategy(
                    request, providers, strategy_config
                )
            case _:
                raise Exception(f"Unsupported load balancing strategy: {strategy}")

    async def _build_provider_info_list(
        self, model_name: str, model_providers: List[Any]
    ) -> List[ProviderInfo]:
        """Build provider information list"""
        providers = []

        for mp in model_providers:
            # Get provider information
            from .database_service import db_service

            provider = db_service.get_provider_by_id(mp.provider_id)
            if not provider:
                continue

            # Get health status from database
            health_status = mp.health_status
            if health_status == "unhealthy":
                continue

            # Build provider information (adapter will be dynamically obtained at execution time)
            provider_info = ProviderInfo(
                name=provider.name,
                adapter=None,  # Adapter will be dynamically obtained at execution time
                weight=mp.weight,
                priority=mp.priority,
                health_status=mp.health_status,
                response_time_avg=mp.response_time_avg,
                success_rate=mp.success_rate,
                cost_per_1k_tokens=mp.cost_per_1k_tokens,
                overall_score=mp.overall_score,
                current_connections=self.provider_connections.get(provider.name, 0),
                last_used_time=self.provider_last_used.get(provider.name, 0),
            )

            providers.append(provider_info)

        return providers

    async def _execute_auto_strategy(
        self, request: ChatRequest, providers: List[ProviderInfo]
    ) -> ChatResponse:
        """Auto select best provider strategy"""
        # Sort by overall score, select the best
        providers.sort(key=lambda p: p.overall_score, reverse=True)

        # Try the best 3 providers
        for provider in providers[:3]:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    async def _execute_specified_provider_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """Specify provider strategy"""
        specified_provider = config.get("specified_provider")
        if not specified_provider:
            raise Exception(
                "Specify provider strategy needs to configure specified_provider parameter"
            )

        # Find the specified provider
        for provider in providers:
            if provider.name == specified_provider:
                return await self._execute_request_with_provider(request, provider)

        raise Exception(f"Specified provider {specified_provider} is unavailable")

    async def _execute_fallback_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """Fallback strategy"""
        preferred_provider = config.get("preferred_provider")

        # If there is a preferred provider, try first
        if preferred_provider:
            for provider in providers:
                if provider.name == preferred_provider:
                    try:
                        return await self._execute_request_with_provider(
                            request, provider
                        )
                    except Exception as e:
                        logger.info(
                            f"Preferred provider {preferred_provider} failed: {e}"
                        )
                        break

        # Sort by priority and score
        providers.sort(key=lambda p: (p.priority, p.overall_score), reverse=True)

        # Try each provider
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    async def _execute_weighted_round_robin_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """Weighted round robin strategy"""
        model_key = f"{request.model}_round_robin"

        if model_key not in self.round_robin_counters:
            self.round_robin_counters[model_key] = 0

        # Calculate total weight
        total_weight = sum(p.weight for p in providers)
        if total_weight == 0:
            raise Exception("All provider weights are 0")

        # Round robin selection
        current_counter = self.round_robin_counters[model_key]
        self.round_robin_counters[model_key] = (current_counter + 1) % total_weight

        # Select provider based on weight
        current_weight = 0
        for provider in providers:
            current_weight += provider.weight
            if current_counter < current_weight:
                return await self._execute_request_with_provider(request, provider)

        # If round robin fails, use the first available provider
        for provider in providers:
            try:
                return await self._execute_request_with_provider(request, provider)
            except Exception as e:
                logger.info(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    async def _execute_least_connections_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """Least connections strategy"""
        # Sort by current connections
        providers.sort(key=lambda p: p.current_connections)

        # Select provider with the least connections
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    async def _execute_response_time_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """Response time priority strategy"""
        # Sort by response time (shorter is better)
        providers.sort(key=lambda p: p.response_time_avg)

        # Select provider with the shortest response time
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    async def _execute_cost_optimized_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """Cost optimized strategy"""
        max_cost_threshold = config.get(
            "max_cost_threshold", 0.1
        )  # Maximum cost threshold

        # Filter out providers with too high cost
        affordable_providers = [
            p for p in providers if p.cost_per_1k_tokens <= max_cost_threshold
        ]

        if not affordable_providers:
            # If there are no providers that meet the cost requirements, use the cheapest provider
            providers.sort(key=lambda p: p.cost_per_1k_tokens)
            affordable_providers = providers

        # Sort by cost, select the cheapest provider
        affordable_providers.sort(key=lambda p: p.cost_per_1k_tokens)

        for provider in affordable_providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    async def _execute_hybrid_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """Hybrid strategy"""
        # Hybrid strategy: Consider overall score, response time, cost, and connection count
        for provider in providers:
            # Calculate hybrid score
            hybrid_score = (
                provider.overall_score * 0.4
                + (1 - provider.response_time_avg / 10) * 0.3  # Response time score
                + (1 - provider.cost_per_1k_tokens / 0.1) * 0.2  # Cost score
                + (1 - provider.current_connections / 100)
                * 0.1  # Connection count score
            )
            provider.hybrid_score = hybrid_score

        # Sort by hybrid score
        providers.sort(key=lambda p: p.hybrid_score, reverse=True)

        # Select provider with the highest hybrid score
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    async def _execute_request_with_provider(
        self, request: ChatRequest, provider: ProviderInfo
    ) -> ChatResponse:
        """Execute request with specified provider"""
        start_time = time.time()

        try:
            # Update connection count
            self.provider_connections[provider.name] = (
                self.provider_connections.get(provider.name, 0) + 1
            )

            # Get adapter from adapter pool
            from .adapter_pool import adapter_pool

            adapter = await adapter_pool.get_adapter(request.model, provider.name)
            if not adapter:
                raise Exception(f"Cannot get adapter: {request.model}:{provider.name}")

            try:
                # Execute request
                response = await adapter.chat_completion(request)

                # Update last used time
                self.provider_last_used[provider.name] = time.time()

                # Update metrics
                response_time = time.time() - start_time
                await self._update_provider_metrics(provider.name, response_time, True)

                # Update API key usage count in database
                await self._update_api_key_usage(adapter, True)

                return response
            finally:
                # Release adapter back to pool
                await adapter_pool.release_adapter(
                    adapter, request.model, provider.name
                )

        except Exception as e:
            # Update failure metrics
            response_time = time.time() - start_time
            await self._update_provider_metrics(provider.name, response_time, False)

            # Update API key usage count in database (even for failed requests)
            try:
                from .adapter_pool import adapter_pool

                adapter = await adapter_pool.get_adapter(request.model, provider.name)
                if adapter:
                    await self._update_api_key_usage(adapter, False)
            except Exception as update_error:
                logger.warning(
                    f"Failed to update API key usage for failed request: {update_error}"
                )

            raise
        finally:
            # Decrease connection count
            self.provider_connections[provider.name] = max(
                0, self.provider_connections.get(provider.name, 1) - 1
            )

    async def _get_provider_adapter(
        self, model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """Get provider adapter"""
        try:
            from .adapter_pool import adapter_pool

            # Get adapter from adapter pool
            adapter = await adapter_pool.get_adapter(model_name, provider_name)
            if adapter:
                logger.info(
                    f"🔄 Get adapter from adapter pool: {model_name}:{provider_name}"
                )
                return adapter
            else:
                logger.info(
                    f"❌ Cannot get adapter from adapter pool: {model_name}:{provider_name}"
                )
                return None

        except Exception as e:
            logger.info(f"Get provider adapter failed: {e}")
            return None

    async def _update_api_key_usage(self, adapter, success: bool):
        """Update API key usage count in database"""
        try:
            # Get API key ID from adapter
            api_key_id = getattr(adapter, "api_key_id", None)
            if not api_key_id:
                # Try to get from model_config
                api_key_id = adapter.model_config.get("api_key_id")

            if api_key_id:
                # Update usage count in database
                from .database_service import db_service

                db_service.update_api_key_usage(api_key_id, increment=True)
                logger.info(f"Updated API key usage count for key {api_key_id}")
            else:
                logger.warning("Cannot find API key ID for usage tracking")

        except Exception as e:
            logger.error(f"Failed to update API key usage count: {e}")

    async def _update_provider_metrics(
        self, provider_name: str, response_time: float, success: bool
    ):
        """Update provider metrics"""
        try:
            # Here can call database service to update metrics
            # Simplified processing, actually should update metrics in database
            pass
        except Exception as e:
            logger.info(f"Update provider metrics failed: {e}")

    def get_strategy_info(self) -> Dict[str, Any]:
        """Get strategy information"""
        return {
            "available_strategies": [
                strategy.value for strategy in LoadBalancingStrategy
            ],
            "current_connections": self.provider_connections,
            "last_used_times": self.provider_last_used,
            "round_robin_counters": self.round_robin_counters,
        }


# Global strategy manager instance
strategy_manager = LoadBalancingStrategyManager()
