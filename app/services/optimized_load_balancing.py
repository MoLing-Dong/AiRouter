import asyncio
import time
import random
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
from dataclasses import dataclass
from functools import lru_cache
from ..core.adapters import ChatRequest, ChatResponse
from ..core.adapters.base import BaseAdapter, HealthStatus
from .database_service import db_service
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategy enumeration"""

    AUTO = "auto"
    SPECIFIED_PROVIDER = "specified_provider"
    FALLBACK = "fallback"
    WEIGHTED_ROUND_ROBIN = "weighted_round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RESPONSE_TIME = "response_time"
    COST_OPTIMIZED = "cost_optimized"
    HYBRID = "hybrid"


@dataclass
class ProviderInfo:
    """Provider information with performance metrics"""

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
    hybrid_score: float = 0.0


class OptimizedLoadBalancingManager:
    """High-performance load balancing strategy manager"""

    def __init__(self):
        # 使用缓存减少重复计算
        self._strategy_cache: Dict[str, Callable] = {}
        self._provider_cache: Dict[str, List[ProviderInfo]] = {}
        self._cache_ttl = 30.0  # 缓存30秒
        self._last_cache_update = 0.0

        # 性能统计
        self.stats = {
            "total_requests": 0,
            "strategy_usage": {},
            "avg_response_time": 0.0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

        # 初始化策略映射
        self._init_strategy_mapping()

    def _init_strategy_mapping(self):
        """初始化策略映射，减少运行时查找"""
        self._strategy_cache = {
            LoadBalancingStrategy.AUTO: self._execute_auto_strategy,
            LoadBalancingStrategy.SPECIFIED_PROVIDER: self._execute_specified_provider_strategy,
            LoadBalancingStrategy.FALLBACK: self._execute_fallback_strategy,
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: self._execute_weighted_round_robin_strategy,
            LoadBalancingStrategy.LEAST_CONNECTIONS: self._execute_least_connections_strategy,
            LoadBalancingStrategy.RESPONSE_TIME: self._execute_response_time_strategy,
            LoadBalancingStrategy.COST_OPTIMIZED: self._execute_cost_optimized_strategy,
            LoadBalancingStrategy.HYBRID: self._execute_hybrid_strategy,
        }

    async def execute_strategy(
        self,
        request: ChatRequest,
        model_providers: List[Any],
        strategy: str,
        strategy_config: Dict[str, Any] = None,
    ) -> ChatResponse:
        """执行指定的负载均衡策略 - 优化版本"""
        start_time = time.time()
        self.stats["total_requests"] += 1

        if strategy_config is None:
            strategy_config = {}

        # 获取策略函数
        strategy_func = self._strategy_cache.get(strategy)
        if not strategy_func:
            raise ValueError(f"Unknown strategy: {strategy}")

        # 构建提供商信息列表（使用缓存）
        providers = await self._get_cached_provider_info(request.model, model_providers)

        if not providers:
            raise Exception(f"Model {request.model} has no available providers")

        try:
            # 执行策略
            response = await strategy_func(request, providers, strategy_config)

            # 更新统计信息
            response_time = time.time() - start_time
            self._update_stats(strategy, response_time)

            return response

        except Exception as e:
            logger.error(f"Strategy execution failed: {e}")
            # 尝试降级策略
            return await self._execute_fallback_strategy(
                request, providers, strategy_config
            )

    async def _get_cached_provider_info(
        self, model: str, model_providers: List[Any]
    ) -> List[ProviderInfo]:
        """获取缓存的提供商信息"""
        current_time = time.time()
        cache_key = f"{model}:{hash(str(model_providers))}"

        # 检查缓存是否有效
        if (
            cache_key in self._provider_cache
            and current_time - self._last_cache_update < self._cache_ttl
        ):
            self.stats["cache_hits"] += 1
            return self._provider_cache[cache_key]

        # 缓存失效，重新构建
        self.stats["cache_misses"] += 1
        providers = await self._build_provider_info_list_optimized(
            model, model_providers
        )
        self._provider_cache[cache_key] = providers
        self._last_cache_update = current_time

        return providers

    async def _build_provider_info_list_optimized(
        self, model: str, model_providers: List[Any]
    ) -> List[ProviderInfo]:
        """优化的提供商信息构建"""
        providers = []

        # 并行处理提供商信息
        tasks = []
        for provider_data in model_providers:
            task = self._build_single_provider_info(provider_data)
            tasks.append(task)

        # 等待所有任务完成
        provider_infos = await asyncio.gather(*tasks, return_exceptions=True)

        # 过滤有效结果
        for info in provider_infos:
            if isinstance(info, ProviderInfo):
                providers.append(info)
            elif isinstance(info, Exception):
                logger.warning(f"Failed to build provider info: {info}")

        # 按优先级和分数排序
        providers.sort(key=lambda p: (p.priority, p.overall_score), reverse=True)

        return providers

    async def _build_single_provider_info(self, provider_data: Any) -> ProviderInfo:
        """构建单个提供商信息"""
        try:
            # 异步获取健康状态
            health_status = await self._get_provider_health_async(provider_data)

            # 计算性能分数
            performance_score = self._calculate_performance_score(provider_data)

            return ProviderInfo(
                name=provider_data.get("name", ""),
                adapter=provider_data.get("adapter"),
                weight=provider_data.get("weight", 1),
                priority=provider_data.get("priority", 0),
                health_status=health_status,
                response_time_avg=provider_data.get("response_time_avg", 0.0),
                success_rate=provider_data.get("success_rate", 1.0),
                cost_per_1k_tokens=provider_data.get("cost_per_1k_tokens", 0.0),
                overall_score=performance_score,
                current_connections=provider_data.get("current_connections", 0),
                last_used_time=provider_data.get("last_used_time", 0.0),
            )
        except Exception as e:
            logger.error(f"Failed to build provider info: {e}")
            raise

    async def _get_provider_health_async(self, provider_data: Any) -> str:
        """异步获取提供商健康状态"""
        try:
            adapter = provider_data.get("adapter")
            if hasattr(adapter, "get_health_status"):
                # 使用超时避免长时间等待
                return await asyncio.wait_for(adapter.get_health_status(), timeout=2.0)
            return "unknown"
        except asyncio.TimeoutError:
            return "timeout"
        except Exception:
            return "error"

    def _calculate_performance_score(self, provider_data: Any) -> float:
        """计算性能分数"""
        response_time = provider_data.get("response_time_avg", 0.0)
        success_rate = provider_data.get("success_rate", 1.0)
        cost = provider_data.get("cost_per_1k_tokens", 0.0)

        # 归一化分数计算
        time_score = max(0, 1 - (response_time / 10.0))  # 10秒为基准
        cost_score = max(0, 1 - (cost / 0.1))  # 0.1美元为基准

        # 加权平均
        return time_score * 0.4 + success_rate * 0.4 + cost_score * 0.2

    def _update_stats(self, strategy: str, response_time: float):
        """更新统计信息"""
        if strategy not in self.stats["strategy_usage"]:
            self.stats["strategy_usage"][strategy] = 0
        self.stats["strategy_usage"][strategy] += 1

        # 更新平均响应时间
        total_requests = self.stats["total_requests"]
        current_avg = self.stats["avg_response_time"]
        self.stats["avg_response_time"] = (
            current_avg * (total_requests - 1) + response_time
        ) / total_requests

    # 优化的策略实现
    async def _execute_auto_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """自动策略 - 选择最优提供商"""
        # 使用混合评分选择最佳提供商
        best_provider = max(providers, key=lambda p: p.overall_score)
        return await self._execute_request_with_provider(request, best_provider)

    async def _execute_weighted_round_robin_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """加权轮询策略 - 优化版本"""
        # 使用预计算的权重分布
        total_weight = sum(p.weight for p in providers)
        if total_weight == 0:
            raise Exception("All provider weights are 0")

        # 使用哈希选择，避免状态维护
        request_hash = hash(f"{request.model}:{request.messages}")
        selected_index = request_hash % total_weight

        current_weight = 0
        for provider in providers:
            current_weight += provider.weight
            if selected_index < current_weight:
                return await self._execute_request_with_provider(request, provider)

        # 降级到第一个可用提供商
        return await self._execute_request_with_provider(request, providers[0])

    async def _execute_least_connections_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """最少连接数策略 - 优化版本"""
        # 快速排序并选择
        min_connections = min(p.current_connections for p in providers)
        candidates = [p for p in providers if p.current_connections == min_connections]

        # 在候选者中选择性能最好的
        best_candidate = max(candidates, key=lambda p: p.overall_score)
        return await self._execute_request_with_provider(request, best_candidate)

    async def _execute_cost_optimized_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """成本优化策略 - 优化版本"""
        # 按成本排序，但考虑性能
        cost_threshold = config.get("max_cost", float("inf"))
        affordable_providers = [
            p for p in providers if p.cost_per_1k_tokens <= cost_threshold
        ]

        if not affordable_providers:
            affordable_providers = providers

        # 选择成本效益比最高的
        best_provider = max(
            affordable_providers,
            key=lambda p: p.overall_score / max(p.cost_per_1k_tokens, 0.001),
        )

        return await self._execute_request_with_provider(request, best_provider)

    async def _execute_hybrid_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """混合策略 - 综合考虑多个因素"""
        # 计算混合评分
        for provider in providers:
            provider.hybrid_score = self._calculate_hybrid_score(
                provider, request, config
            )

        # 选择混合评分最高的
        best_provider = max(providers, key=lambda p: p.hybrid_score)
        return await self._execute_request_with_provider(request, best_provider)

    def _calculate_hybrid_score(
        self, provider: ProviderInfo, request: ChatRequest, config: Dict[str, Any]
    ) -> float:
        """计算混合评分"""
        # 基础分数
        base_score = provider.overall_score

        # 时间权重（根据请求类型调整）
        time_weight = 1.0
        if len(request.messages) > 10:  # 长对话
            time_weight = 1.2
        elif len(request.messages) < 3:  # 短对话
            time_weight = 0.8

        # 成本权重
        cost_weight = 1.0
        if config.get("cost_sensitive", False):
            cost_weight = 1.5

        # 健康状态权重
        health_weight = 1.0
        if provider.health_status == "healthy":
            health_weight = 1.2
        elif provider.health_status == "degraded":
            health_weight = 0.8

        return base_score * time_weight * cost_weight * health_weight

    async def _execute_request_with_provider(
        self, request: ChatRequest, provider: ProviderInfo
    ) -> ChatResponse:
        """执行请求 - 优化版本"""
        try:
            # 更新连接数
            provider.current_connections += 1
            provider.last_used_time = time.time()

            # 执行请求
            response = await provider.adapter.chat(request)

            # 更新性能指标
            self._update_provider_metrics(provider, True, 0.0)

            return response

        except Exception as e:
            # 更新失败指标
            self._update_provider_metrics(provider, False, 0.0)
            raise
        finally:
            # 减少连接数
            provider.current_connections = max(0, provider.current_connections - 1)

    def _update_provider_metrics(
        self, provider: ProviderInfo, success: bool, response_time: float
    ):
        """更新提供商指标"""
        # 更新成功率
        if success:
            provider.success_rate = min(1.0, provider.success_rate + 0.01)
        else:
            provider.success_rate = max(0.0, provider.success_rate - 0.05)

        # 更新响应时间
        if response_time > 0:
            if provider.response_time_avg == 0:
                provider.response_time_avg = response_time
            else:
                # 指数移动平均
                alpha = 0.1
                provider.response_time_avg = (
                    alpha * response_time + (1 - alpha) * provider.response_time_avg
                )

    async def _execute_fallback_strategy(
        self,
        request: ChatRequest,
        providers: List[ProviderInfo],
        config: Dict[str, Any],
    ) -> ChatResponse:
        """故障转移策略"""
        # 按健康状态排序
        healthy_providers = [p for p in providers if p.health_status == "healthy"]
        if not healthy_providers:
            healthy_providers = providers

        # 尝试每个提供商
        for provider in healthy_providers:
            try:
                return await self._execute_request_with_provider(request, provider)
            except Exception as e:
                logger.warning(f"Provider {provider.name} failed: {e}")
                continue

        raise Exception("All providers are unavailable")

    def get_stats(self) -> Dict[str, Any]:
        """获取负载均衡统计信息"""
        return {
            "total_requests": self.stats["total_requests"],
            "strategy_usage": self.stats["strategy_usage"],
            "avg_response_time": self.stats["avg_response_time"],
            "cache_hits": self.stats["cache_hits"],
            "cache_misses": self.stats["cache_misses"],
            "cache_hit_rate": (
                self.stats["cache_hits"]
                / max(self.stats["cache_hits"] + self.stats["cache_misses"], 1)
            ),
        }
