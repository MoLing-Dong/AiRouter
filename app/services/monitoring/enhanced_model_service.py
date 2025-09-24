"""
增强模型服务 - 集成异步数据库、Redis缓存和性能优化
提供高性能的模型管理和查询服务
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import redis.asyncio as redis
from sqlalchemy import text

from ..database.async_database_service import async_db_service
# from app.models.sqlmodel_models import (
#     LLMModel, LLMProvider, LLMModelProvider, QueryBuilder,
#     HealthStatus, ModelResponse, PerformanceMetrics
# )
from config.settings import settings
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class EnhancedModelService:
    """增强模型服务 - 集成缓存、异步数据库和性能优化"""

    def __init__(self):
        # Redis连接配置
        self.redis_client: Optional[redis.Redis] = None
        self.cache_enabled = True
        self.cache_ttl = {
            "models": 300,  # 5分钟
            "providers": 600,  # 10分钟
            "performance": 180,  # 3分钟
            "health": 60,  # 1分钟
        }
        
        # 性能监控
        self.performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "db_queries": 0,
            "avg_query_time": 0.0,
        }
        
        # 批处理配置
        self.batch_size = 50
        self.batch_timeout = 5.0  # 5秒

    async def initialize(self):
        """初始化服务"""
        try:
            # 初始化Redis连接
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            
            # 测试Redis连接
            await self.redis_client.ping()
            logger.info("✅ Redis connection established")
            
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e}. Cache disabled.")
            self.cache_enabled = False

    async def close(self):
        """关闭服务"""
        if self.redis_client:
            await self.redis_client.close()
        await async_db_service.close()

    # ==================== 缓存管理 ====================

    def _get_cache_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [prefix] + [str(arg) for arg in args]
        if kwargs:
            key_parts.append(json.dumps(kwargs, sort_keys=True))
        return ":".join(key_parts)

    async def _get_from_cache(self, cache_key: str) -> Optional[Any]:
        """从缓存获取数据"""
        if not self.cache_enabled or not self.redis_client:
            return None
            
        try:
            data = await self.redis_client.get(cache_key)
            if data:
                self.performance_metrics["cache_hits"] += 1
                return json.loads(data)
            else:
                self.performance_metrics["cache_misses"] += 1
                return None
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
            return None

    async def _set_cache(self, cache_key: str, data: Any, ttl: int):
        """设置缓存数据"""
        if not self.cache_enabled or not self.redis_client:
            return
            
        try:
            await self.redis_client.setex(
                cache_key, 
                ttl, 
                json.dumps(data, default=str)
            )
        except Exception as e:
            logger.debug(f"Cache set error: {e}")

    async def _invalidate_cache_pattern(self, pattern: str):
        """按模式删除缓存"""
        if not self.cache_enabled or not self.redis_client:
            return
            
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                await self.redis_client.delete(*keys)
                logger.debug(f"Invalidated {len(keys)} cache keys with pattern: {pattern}")
        except Exception as e:
            logger.debug(f"Cache invalidation error: {e}")

    # ==================== 模型查询服务 ====================

    async def get_all_models_enhanced(
        self, 
        is_enabled: Optional[bool] = None,
        include_relationships: bool = True,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取所有模型（增强版） - 支持缓存和性能优化
        """
        cache_key = self._get_cache_key(
            "models:all", is_enabled, include_relationships
        )
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

        # 从数据库查询
        start_time = datetime.now()
        
        if include_relationships:
            models_data = await async_db_service.get_all_models_with_relationships(is_enabled)
        else:
            # 简化查询，只获取基本信息
            async with async_db_service.get_session() as session:
                from sqlalchemy import select
                query = select(LLMModel)
                if is_enabled is not None:
                    query = query.where(LLMModel.is_enabled == is_enabled)
                
                result = await session.execute(query)
                models = result.scalars().all()
                
                models_data = [
                    {
                        "id": model.id,
                        "name": model.name,
                        "llm_type": model.llm_type,
                        "description": model.description,
                        "is_enabled": model.is_enabled,
                        "created_at": model.created_at,
                        "updated_at": model.updated_at,
                    }
                    for model in models
                ]

        query_time = (datetime.now() - start_time).total_seconds()
        self.performance_metrics["db_queries"] += 1
        
        # 更新平均查询时间
        total_queries = self.performance_metrics["db_queries"]
        current_avg = self.performance_metrics["avg_query_time"]
        self.performance_metrics["avg_query_time"] = (
            current_avg * (total_queries - 1) + query_time
        ) / total_queries

        # 缓存结果
        if use_cache:
            await self._set_cache(cache_key, models_data, self.cache_ttl["models"])

        logger.info(
            f"✅ Retrieved {len(models_data)} models in {query_time:.3f}s "
            f"(cached: {use_cache and cached_data is not None})"
        )
        
        return models_data

    async def get_model_by_name_enhanced(
        self, 
        model_name: str, 
        include_relationships: bool = True,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个模型（增强版）
        """
        cache_key = self._get_cache_key("models:single", model_name, include_relationships)
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

        # 从数据库查询
        model_data = await async_db_service.get_model_by_name_optimized(
            model_name, include_relationships
        )

        # 缓存结果
        if use_cache and model_data:
            await self._set_cache(cache_key, model_data, self.cache_ttl["models"])

        return model_data

    async def get_healthy_models(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        获取健康的模型（至少有一个健康的提供商）
        """
        cache_key = self._get_cache_key("models:healthy")
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

        # 使用优化查询
        async with async_db_service.get_session() as session:
            query = QueryBuilder.get_models_with_healthy_providers()
            result = await session.execute(query)
            models = result.scalars().all()
            
            models_data = [
                {
                    "id": model.id,
                    "name": model.name,
                    "llm_type": model.llm_type,
                    "description": model.description,
                    "is_enabled": model.is_enabled,
                }
                for model in models
            ]

        # 缓存结果（较短TTL，因为健康状态变化较快）
        if use_cache:
            await self._set_cache(cache_key, models_data, self.cache_ttl["health"])

        return models_data

    # ==================== 性能分析服务 ====================

    async def get_model_performance_analysis(
        self, 
        model_name: str, 
        days: int = 7,
        use_cache: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        获取模型性能分析
        """
        cache_key = self._get_cache_key("performance:model", model_name, days)
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

        # 获取模型信息
        model_data = await self.get_model_by_name_enhanced(model_name, True, use_cache)
        if not model_data:
            return None

        # 计算性能指标
        total_requests = 0
        total_successful = 0
        total_cost = 0.0
        response_times = []
        provider_count = 0

        for provider in model_data.get("providers", []):
            if provider.get("is_enabled"):
                provider_count += 1
                total_requests += provider.get("total_requests", 0)
                total_successful += provider.get("successful_requests", 0) 
                total_cost += provider.get("total_cost", 0.0)
                
                if provider.get("response_time_avg", 0) > 0:
                    response_times.append(provider["response_time_avg"])

        # 计算综合指标
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0.0
        success_rate = total_successful / total_requests if total_requests > 0 else 0.0
        avg_score = sum(p.get("overall_score", 0) for p in model_data.get("providers", [])) / provider_count if provider_count > 0 else 0.0

        performance_data = {
            "model_name": model_name,
            "model_id": model_data["id"],
            "analysis_period_days": days,
            "provider_count": provider_count,
            "total_requests": total_requests,
            "successful_requests": total_successful,
            "failed_requests": total_requests - total_successful,
            "success_rate": round(success_rate, 3),
            "avg_response_time": round(avg_response_time, 3),
            "total_cost": round(total_cost, 4),
            "cost_per_request": round(total_cost / total_requests, 6) if total_requests > 0 else 0.0,
            "overall_score": round(avg_score, 3),
            "providers": model_data.get("providers", []),
            "generated_at": datetime.utcnow().isoformat(),
        }

        # 缓存结果
        if use_cache:
            await self._set_cache(cache_key, performance_data, self.cache_ttl["performance"])

        return performance_data

    async def get_provider_performance_summary(
        self, 
        days: int = 7,
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        获取提供商性能汇总
        """
        cache_key = self._get_cache_key("performance:providers", days)
        
        # 尝试从缓存获取
        if use_cache:
            cached_data = await self._get_from_cache(cache_key)
            if cached_data:
                return cached_data

        # 从异步数据库服务获取聚合数据
        providers_data = await async_db_service.get_provider_performance_aggregated(days)

        # 缓存结果
        if use_cache:
            await self._set_cache(cache_key, providers_data, self.cache_ttl["performance"])

        return providers_data

    # ==================== 批量操作服务 ====================

    async def batch_update_model_metrics(
        self, 
        updates: List[Dict[str, Any]],
        invalidate_cache: bool = True
    ) -> bool:
        """
        批量更新模型指标
        """
        if not updates:
            return True

        # 执行批量更新
        success = await async_db_service.batch_update_model_provider_metrics(updates)
        
        if success and invalidate_cache:
            # 清理相关缓存
            await self._invalidate_cache_pattern("models:*")
            await self._invalidate_cache_pattern("performance:*")
            logger.info(f"🧹 Invalidated cache after batch update of {len(updates)} records")

        return success

    async def batch_health_check(
        self, 
        model_provider_pairs: List[Tuple[str, str]]
    ) -> Dict[str, Any]:
        """
        批量健康检查
        """
        results = {
            "total_checked": len(model_provider_pairs),
            "healthy": 0,
            "degraded": 0,
            "unhealthy": 0,
            "details": []
        }

        # 并发执行健康检查
        tasks = []
        for model_name, provider_name in model_provider_pairs:
            task = self._check_model_provider_health(model_name, provider_name)
            tasks.append(task)

        # 等待所有检查完成
        health_results = await asyncio.gather(*tasks, return_exceptions=True)

        # 统计结果
        for i, result in enumerate(health_results):
            if isinstance(result, Exception):
                logger.error(f"Health check failed: {result}")
                continue

            results["details"].append(result)
            status = result.get("status", "unhealthy")
            results[status] += 1

        return results

    async def _check_model_provider_health(
        self, 
        model_name: str, 
        provider_name: str
    ) -> Dict[str, Any]:
        """
        检查单个模型-提供商的健康状态
        """
        try:
            # 这里应该实现实际的健康检查逻辑
            # 例如发送测试请求、检查响应时间等
            
            # 模拟健康检查（实际实现时需要根据具体需求）
            start_time = datetime.now()
            
            # 检查数据库中的健康状态
            model_data = await self.get_model_by_name_enhanced(model_name, True, True)
            if not model_data:
                return {
                    "model_name": model_name,
                    "provider_name": provider_name,
                    "status": "unhealthy",
                    "error": "Model not found"
                }

            # 查找对应的提供商
            provider_info = None
            for provider in model_data.get("providers", []):
                if provider.get("provider_name") == provider_name:
                    provider_info = provider
                    break

            if not provider_info:
                return {
                    "model_name": model_name,
                    "provider_name": provider_name,
                    "status": "unhealthy",
                    "error": "Provider not found"
                }

            response_time = (datetime.now() - start_time).total_seconds()
            
            # 基于性能指标判断健康状态
            overall_score = provider_info.get("overall_score", 0)
            if overall_score >= 0.8:
                status = "healthy"
            elif overall_score >= 0.5:
                status = "degraded"
            else:
                status = "unhealthy"

            return {
                "model_name": model_name,
                "provider_name": provider_name,
                "status": status,
                "response_time": round(response_time, 3),
                "overall_score": overall_score,
                "checked_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            return {
                "model_name": model_name,
                "provider_name": provider_name,
                "status": "unhealthy",
                "error": str(e),
                "checked_at": datetime.utcnow().isoformat()
            }

    # ==================== 统计和监控 ====================

    async def get_service_statistics(self) -> Dict[str, Any]:
        """
        获取服务统计信息
        """
        db_stats = await async_db_service.get_database_statistics()
        
        # Redis统计
        redis_stats = {}
        if self.redis_client:
            try:
                info = await self.redis_client.info()
                redis_stats = {
                    "connected_clients": info.get("connected_clients", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0),
                }
            except Exception as e:
                redis_stats = {"error": str(e)}

        # 计算缓存效率
        cache_total = self.performance_metrics["cache_hits"] + self.performance_metrics["cache_misses"]
        cache_hit_rate = (
            self.performance_metrics["cache_hits"] / cache_total * 100
            if cache_total > 0 else 0
        )

        return {
            "database": db_stats,
            "redis": redis_stats,
            "service_performance": {
                **self.performance_metrics,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "cache_enabled": self.cache_enabled,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def clear_all_cache(self):
        """清理所有缓存"""
        if self.redis_client:
            try:
                await self.redis_client.flushdb()
                logger.info("🧹 All cache cleared")
            except Exception as e:
                logger.error(f"Failed to clear cache: {e}")

        # 同时清理数据库服务的缓存
        await async_db_service.clear_cache()


# 全局增强模型服务实例
enhanced_model_service = EnhancedModelService()
