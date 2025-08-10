"""
负载均衡策略管理器
实现各种不同的负载均衡策略
"""

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

# 获取日志器
logger = get_factory_logger()


class LoadBalancingStrategy(str, Enum):
    """负载均衡策略枚举"""

    AUTO = "auto"  # 自动选择最佳供应商
    SPECIFIED_PROVIDER = "specified_provider"  # 指定供应商
    FALLBACK = "fallback"  # 故障转移
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"  # 加权轮询
    LEAST_CONNECTIONS = "least_connections"  # 最少连接数
    RESPONSE_TIME = "response_time"  # 响应时间优先
    COST_OPTIMIZED = "cost_optimized"  # 成本优化
    HYBRID = "hybrid"  # 混合策略


@dataclass
class ProviderInfo:
    """供应商信息"""

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
    hybrid_score: float = 0.0  # 混合策略评分


class LoadBalancingStrategyManager:
    """负载均衡策略管理器"""

    def __init__(self):
        self.provider_connections: Dict[str, int] = {}  # 记录每个供应商的当前连接数
        self.provider_last_used: Dict[str, float] = {}  # 记录每个供应商的最后使用时间
        self.round_robin_counters: Dict[str, int] = {}  # 轮询计数器

    async def execute_strategy(
        self,
        request: ChatRequest,
        model_providers: List[Any],
        strategy: str,
        strategy_config: Dict[str, Any] = None,
    ) -> ChatResponse:
        """执行指定的负载均衡策略"""

        if strategy_config is None:
            strategy_config = {}

        # 构建供应商信息列表
        providers = await self._build_provider_info_list(request.model, model_providers)

        if not providers:
            raise Exception(f"模型 {request.model} 没有可用的供应商")

        # 根据策略选择供应商
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
                raise Exception(f"不支持的负载均衡策略: {strategy}")

    async def _build_provider_info_list(
        self, model_name: str, model_providers: List[Any]
    ) -> List[ProviderInfo]:
        """构建供应商信息列表"""
        providers = []

        for mp in model_providers:
            # 获取供应商信息
            from .database_service import db_service

            provider = db_service.get_provider_by_id(mp.provider_id)
            if not provider:
                continue

            # 从数据库获取健康状态
            health_status = mp.health_status
            if health_status == "unhealthy":
                continue

            # 构建供应商信息（不在这里获取适配器，而是在执行时动态获取）
            provider_info = ProviderInfo(
                name=provider.name,
                adapter=None,  # 适配器将在执行时动态获取
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
        """自动选择最佳供应商策略"""
        # 按综合评分排序，选择最佳的
        providers.sort(key=lambda p: p.overall_score, reverse=True)

        # 尝试前3个最佳供应商
        for provider in providers[:3]:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"供应商 {provider.name} 失败: {e}")
                continue

        raise Exception("所有供应商都不可用")

    async def _execute_specified_provider_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """指定供应商策略"""
        specified_provider = config.get("specified_provider")
        if not specified_provider:
            raise Exception("指定供应商策略需要配置 specified_provider 参数")

        # 查找指定的供应商
        for provider in providers:
            if provider.name == specified_provider:
                return await self._execute_request_with_provider(request, provider)

        raise Exception(f"指定的供应商 {specified_provider} 不可用")

    async def _execute_fallback_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """故障转移策略"""
        preferred_provider = config.get("preferred_provider")

        # 如果有首选供应商，先尝试
        if preferred_provider:
            for provider in providers:
                if provider.name == preferred_provider:
                    try:
                        return await self._execute_request_with_provider(
                            request, provider
                        )
                    except Exception as e:
                        logger.info(f"首选供应商 {preferred_provider} 失败: {e}")
                        break

        # 按优先级和评分排序
        providers.sort(key=lambda p: (p.priority, p.overall_score), reverse=True)

        # 逐个尝试供应商
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"供应商 {provider.name} 失败: {e}")
                continue

        raise Exception("所有供应商都不可用")

    async def _execute_weighted_round_robin_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """加权轮询策略"""
        model_key = f"{request.model}_round_robin"

        if model_key not in self.round_robin_counters:
            self.round_robin_counters[model_key] = 0

        # 计算总权重
        total_weight = sum(p.weight for p in providers)
        if total_weight == 0:
            raise Exception("所有供应商权重都为0")

        # 轮询选择
        current_counter = self.round_robin_counters[model_key]
        self.round_robin_counters[model_key] = (current_counter + 1) % total_weight

        # 根据权重选择供应商
        current_weight = 0
        for provider in providers:
            current_weight += provider.weight
            if current_counter < current_weight:
                return await self._execute_request_with_provider(request, provider)

        # 如果轮询失败，使用第一个可用供应商
        for provider in providers:
            try:
                return await self._execute_request_with_provider(request, provider)
            except Exception as e:
                logger.info(f"供应商 {provider.name} 失败: {e}")
                continue

        raise Exception("所有供应商都不可用")

    async def _execute_least_connections_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """最少连接数策略"""
        # 按当前连接数排序
        providers.sort(key=lambda p: p.current_connections)

        # 选择连接数最少的供应商
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"供应商 {provider.name} 失败: {e}")
                continue

        raise Exception("所有供应商都不可用")

    async def _execute_response_time_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """响应时间优先策略"""
        # 按响应时间排序（响应时间越短越好）
        providers.sort(key=lambda p: p.response_time_avg)

        # 选择响应时间最短的供应商
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"供应商 {provider.name} 失败: {e}")
                continue

        raise Exception("所有供应商都不可用")

    async def _execute_cost_optimized_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """成本优化策略"""
        max_cost_threshold = config.get("max_cost_threshold", 0.1)  # 最大成本阈值

        # 过滤掉成本过高的供应商
        affordable_providers = [
            p for p in providers if p.cost_per_1k_tokens <= max_cost_threshold
        ]

        if not affordable_providers:
            # 如果没有符合成本要求的供应商，使用成本最低的
            providers.sort(key=lambda p: p.cost_per_1k_tokens)
            affordable_providers = providers

        # 按成本排序，选择成本最低的
        affordable_providers.sort(key=lambda p: p.cost_per_1k_tokens)

        for provider in affordable_providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"供应商 {provider.name} 失败: {e}")
                continue

        raise Exception("所有供应商都不可用")

    async def _execute_hybrid_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """混合策略"""
        # 混合策略：综合考虑评分、响应时间、成本和连接数
        for provider in providers:
            # 计算混合评分
            hybrid_score = (
                provider.overall_score * 0.4
                + (1 - provider.response_time_avg / 10) * 0.3  # 响应时间评分
                + (1 - provider.cost_per_1k_tokens / 0.1) * 0.2  # 成本评分
                + (1 - provider.current_connections / 100) * 0.1  # 连接数评分
            )
            provider.hybrid_score = hybrid_score

        # 按混合评分排序
        providers.sort(key=lambda p: p.hybrid_score, reverse=True)

        # 选择混合评分最高的供应商
        for provider in providers:
            try:
                response = await self._execute_request_with_provider(request, provider)
                return response
            except Exception as e:
                logger.info(f"供应商 {provider.name} 失败: {e}")
                continue

        raise Exception("所有供应商都不可用")

    async def _execute_request_with_provider(
        self, request: ChatRequest, provider: ProviderInfo
    ) -> ChatResponse:
        """使用指定供应商执行请求"""
        start_time = time.time()

        try:
            # 更新连接数
            self.provider_connections[provider.name] = (
                self.provider_connections.get(provider.name, 0) + 1
            )

            # 从适配器池获取适配器
            from .adapter_pool import adapter_pool

            adapter = await adapter_pool.get_adapter(request.model, provider.name)
            if not adapter:
                raise Exception(f"无法获取适配器: {request.model}:{provider.name}")

            try:
                # 执行请求
                response = await adapter.chat_completion(request)

                # 更新最后使用时间
                self.provider_last_used[provider.name] = time.time()

                # 更新指标
                response_time = time.time() - start_time
                await self._update_provider_metrics(provider.name, response_time, True)

                return response
            finally:
                # 释放适配器回池
                await adapter_pool.release_adapter(
                    adapter, request.model, provider.name
                )

        except Exception as e:
            # 更新失败指标
            response_time = time.time() - start_time
            await self._update_provider_metrics(provider.name, response_time, False)
            raise
        finally:
            # 减少连接数
            self.provider_connections[provider.name] = max(
                0, self.provider_connections.get(provider.name, 1) - 1
            )

    async def _get_provider_adapter(
        self, model_name: str, provider_name: str
    ) -> Optional[BaseAdapter]:
        """获取供应商适配器"""
        try:
            from .adapter_pool import adapter_pool

            # 从适配器池获取适配器
            adapter = await adapter_pool.get_adapter(model_name, provider_name)
            if adapter:
                logger.info(f"🔄 从适配器池获取适配器: {model_name}:{provider_name}")
                return adapter
            else:
                logger.info(
                    f"❌ 无法从适配器池获取适配器: {model_name}:{provider_name}"
                )
                return None

        except Exception as e:
            logger.info(f"获取供应商适配器失败: {e}")
            return None

    async def _update_provider_metrics(
        self, provider_name: str, response_time: float, success: bool
    ):
        """更新供应商指标"""
        try:
            # 这里可以调用数据库服务更新指标
            # 简化处理，实际应该更新数据库中的指标
            pass
        except Exception as e:
            logger.info(f"更新供应商指标失败: {e}")

    def get_strategy_info(self) -> Dict[str, Any]:
        """获取策略信息"""
        return {
            "available_strategies": [
                strategy.value for strategy in LoadBalancingStrategy
            ],
            "current_connections": self.provider_connections,
            "last_used_times": self.provider_last_used,
            "round_robin_counters": self.round_robin_counters,
        }


# 全局策略管理器实例
strategy_manager = LoadBalancingStrategyManager()
