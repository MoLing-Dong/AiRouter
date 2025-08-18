from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, joinedload, selectinload
from sqlalchemy.pool import QueuePool
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import time
import asyncio
from functools import lru_cache
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
from .transaction_manager import DatabaseTransactionManager

logger = get_factory_logger()


class OptimizedDatabaseService:
    """High-performance database service with query optimization"""

    def __init__(self):
        # 优化的数据库连接池配置
        self.engine = create_engine(
            settings.DATABASE_URL,
            poolclass=QueuePool,
            pool_pre_ping=True,
            pool_recycle=3600,  # 1小时回收连接
            pool_size=20,  # 增加连接池大小
            max_overflow=30,  # 增加最大溢出连接
            pool_timeout=30,  # 连接超时
            echo=settings.DEBUG,
        )

        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # 初始化事务管理器
        self.tx_manager = DatabaseTransactionManager(self.SessionLocal)

        # 创建表
        Base.metadata.create_all(bind=self.engine)

        # 查询缓存
        self._query_cache = {}
        self._cache_ttl = 60.0  # 缓存60秒

        # 性能统计
        self.stats = {
            "total_queries": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "slow_queries": 0,
            "avg_query_time": 0.0,
        }

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def _get_cache_key(self, method: str, *args, **kwargs) -> str:
        """生成缓存键"""
        return f"{method}:{hash(str(args) + str(sorted(kwargs.items())))}"

    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """检查缓存是否有效"""
        return time.time() - cache_entry["timestamp"] < self._cache_ttl

    def _update_stats(self, query_time: float, cache_hit: bool = False):
        """更新统计信息"""
        self.stats["total_queries"] += 1

        if cache_hit:
            self.stats["cache_hits"] += 1
        else:
            self.stats["cache_misses"] += 1

        # 更新平均查询时间
        total_queries = self.stats["total_queries"]
        current_avg = self.stats["avg_query_time"]
        self.stats["avg_query_time"] = (
            current_avg * (total_queries - 1) + query_time
        ) / total_queries

        # 记录慢查询
        if query_time > 1.0:  # 超过1秒的查询
            self.stats["slow_queries"] += 1

    @lru_cache(maxsize=1000)
    def get_model_by_name_cached(
        self, model_name: str, is_enabled: bool = None
    ) -> Optional[LLMModel]:
        """带缓存的模型查询"""
        start_time = time.time()

        try:
            with self.get_session() as session:
                query = session.query(LLMModel).filter(LLMModel.name == model_name)
                if is_enabled is not None:
                    query = query.filter(LLMModel.is_enabled == is_enabled)

                model = query.first()

                query_time = time.time() - start_time
                self._update_stats(query_time, True)  # 缓存命中

                return model
        except Exception as e:
            logger.error(f"Failed to get model by name: {e}")
            return None

    def get_all_models_optimized(self, is_enabled: Optional[bool] = None) -> List[Any]:
        """优化的模型查询 - 使用JOIN减少查询次数"""
        start_time = time.time()

        try:
            with self.get_session() as session:
                # 使用JOIN一次性获取所有相关数据
                query = session.query(LLMModel).options(
                    selectinload(LLMModel.providers),
                    selectinload(LLMModel.capabilities),
                    selectinload(LLMModel.parameters),
                )

                if is_enabled is not None:
                    query = query.filter(LLMModel.is_enabled == is_enabled)

                # 添加排序和限制
                models = query.order_by(LLMModel.name).all()

                query_time = time.time() - start_time
                self._update_stats(query_time)

                return models
        except Exception as e:
            logger.warning(f"Failed to get all models: {e}")
            return []

    def get_model_with_providers_optimized(
        self, model_name: str
    ) -> Optional[Dict[str, Any]]:
        """优化的模型和提供商查询 - 单次JOIN查询"""
        start_time = time.time()

        try:
            with self.get_session() as session:
                # 使用原生SQL优化查询
                sql = text(
                    """
                    SELECT 
                        m.id as model_id,
                        m.name as model_name,
                        m.llm_type,
                        m.description,
                        m.is_enabled,
                        m.created_at,
                        m.updated_at,
                        p.id as provider_id,
                        p.name as provider_name,
                        p.base_url,
                        p.api_key,
                        mp.weight,
                        mp.priority,
                        mp.health_status,
                        mp.is_enabled as provider_enabled
                    FROM llm_models m
                    LEFT JOIN llm_model_providers mp ON m.id = mp.llm_id
                    LEFT JOIN llm_providers p ON mp.provider_id = p.id
                    WHERE m.name = :model_name AND m.is_enabled = true
                    ORDER BY mp.priority DESC, mp.weight DESC
                """
                )

                result = session.execute(sql, {"model_name": model_name})

                # 构建结果
                model_data = None
                providers = []

                for row in result:
                    if model_data is None:
                        model_data = {
                            "id": row.model_id,
                            "name": row.model_name,
                            "llm_type": row.llm_type,
                            "description": row.description,
                            "is_enabled": row.is_enabled,
                            "created_at": row.created_at,
                            "updated_at": row.updated_at,
                            "providers": [],
                        }

                    if row.provider_id:
                        providers.append(
                            {
                                "id": row.provider_id,
                                "name": row.provider_name,
                                "base_url": row.base_url,
                                "api_key": row.api_key,
                                "weight": row.weight,
                                "priority": row.priority,
                                "health_status": row.health_status,
                                "is_enabled": row.provider_enabled,
                            }
                        )

                if model_data:
                    model_data["providers"] = providers

                query_time = time.time() - start_time
                self._update_stats(query_time)

                return model_data

        except Exception as e:
            logger.error(f"Failed to get model with providers: {e}")
            return None

    def get_all_models_capabilities_batch_optimized(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """优化的批量能力查询 - 使用窗口函数"""
        start_time = time.time()

        try:
            with self.get_session() as session:
                # 使用窗口函数优化查询
                sql = text(
                    """
                    WITH model_capabilities AS (
                        SELECT 
                            mc.model_id,
                            mc.capability_id,
                            c.capability_name,
                            c.description,
                            ROW_NUMBER() OVER (PARTITION BY mc.model_id ORDER BY c.capability_name) as rn
                        FROM llm_model_capabilities mc
                        JOIN capabilities c ON mc.capability_id = c.capability_id
                        WHERE mc.model_id = ANY(:model_ids)
                    )
                    SELECT 
                        model_id,
                        capability_id,
                        capability_name,
                        description
                    FROM model_capabilities
                    ORDER BY model_id, rn
                """
                )

                result = session.execute(sql, {"model_ids": model_ids})

                # 构建结果
                capabilities_by_model = {}
                for row in result:
                    if row.model_id not in capabilities_by_model:
                        capabilities_by_model[row.model_id] = []

                    capabilities_by_model[row.model_id].append(
                        {
                            "capability_id": row.capability_id,
                            "capability_name": row.capability_name,
                            "description": row.description,
                        }
                    )

                query_time = time.time() - start_time
                self._update_stats(query_time)

                return capabilities_by_model

        except Exception as e:
            logger.warning(f"Failed to get batch capabilities: {e}")
            return {}

    def get_all_models_providers_batch_optimized(
        self, model_ids: List[int]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """优化的批量提供商查询 - 使用CTE和窗口函数"""
        start_time = time.time()

        try:
            with self.get_session() as session:
                # 使用CTE优化复杂查询
                sql = text(
                    """
                    WITH model_providers AS (
                        SELECT 
                            mp.llm_id,
                            mp.provider_id,
                            mp.weight,
                            mp.priority,
                            mp.health_status,
                            mp.is_enabled,
                            p.name as provider_name,
                            p.base_url,
                            p.provider_type,
                            ROW_NUMBER() OVER (
                                PARTITION BY mp.llm_id 
                                ORDER BY mp.priority DESC, mp.weight DESC
                            ) as provider_rank
                        FROM llm_model_providers mp
                        JOIN llm_providers p ON mp.provider_id = p.id
                        WHERE mp.llm_id = ANY(:model_ids) AND mp.is_enabled = true
                    )
                    SELECT 
                        llm_id,
                        provider_id,
                        provider_name,
                        base_url,
                        provider_type,
                        weight,
                        priority,
                        health_status,
                        is_enabled
                    FROM model_providers
                    WHERE provider_rank <= 10  -- 限制每个模型最多10个提供商
                    ORDER BY llm_id, provider_rank
                """
                )

                result = session.execute(sql, {"model_ids": model_ids})

                # 构建结果
                providers_by_model = {}
                for row in result:
                    if row.llm_id not in providers_by_model:
                        providers_by_model[row.llm_id] = []

                    providers_by_model[row.llm_id].append(
                        {
                            "provider_id": row.provider_id,
                            "provider_name": row.provider_name,
                            "base_url": row.base_url,
                            "provider_type": row.provider_type,
                            "weight": row.weight,
                            "priority": row.priority,
                            "health_status": row.health_status,
                            "is_enabled": row.is_enabled,
                        }
                    )

                query_time = time.time() - start_time
                self._update_stats(query_time)

                return providers_by_model

        except Exception as e:
            logger.warning(f"Failed to get batch providers: {e}")
            return {}

    def get_provider_performance_stats(
        self, provider_id: int, days: int = 7
    ) -> Dict[str, Any]:
        """获取提供商性能统计 - 使用聚合查询"""
        start_time = time.time()

        try:
            with self.get_session() as session:
                # 使用聚合查询获取性能统计
                sql = text(
                    """
                    SELECT 
                        COUNT(*) as total_requests,
                        AVG(response_time) as avg_response_time,
                        MIN(response_time) as min_response_time,
                        MAX(response_time) as max_response_time,
                        COUNT(CASE WHEN success = true THEN 1 END) as successful_requests,
                        COUNT(CASE WHEN success = false THEN 1 END) as failed_requests,
                        AVG(CASE WHEN success = true THEN response_time END) as avg_success_time,
                        AVG(CASE WHEN success = false THEN response_time END) as avg_failure_time
                    FROM provider_performance_logs
                    WHERE provider_id = :provider_id 
                    AND created_at >= NOW() - INTERVAL ':days days'
                """
                )

                result = session.execute(
                    sql, {"provider_id": provider_id, "days": days}
                )
                row = result.first()

                if row:
                    stats = {
                        "total_requests": row.total_requests or 0,
                        "avg_response_time": float(row.avg_response_time or 0),
                        "min_response_time": float(row.min_response_time or 0),
                        "max_response_time": float(row.max_response_time or 0),
                        "successful_requests": row.successful_requests or 0,
                        "failed_requests": row.failed_requests or 0,
                        "success_rate": (row.successful_requests or 0)
                        / max(row.total_requests or 1, 1),
                        "avg_success_time": float(row.avg_success_time or 0),
                        "avg_failure_time": float(row.avg_failure_time or 0),
                    }
                else:
                    stats = {
                        "total_requests": 0,
                        "avg_response_time": 0.0,
                        "min_response_time": 0.0,
                        "max_response_time": 0.0,
                        "successful_requests": 0,
                        "failed_requests": 0,
                        "success_rate": 0.0,
                        "avg_success_time": 0.0,
                        "avg_failure_time": 0.0,
                    }

                query_time = time.time() - start_time
                self._update_stats(query_time)

                return stats

        except Exception as e:
            logger.error(f"Failed to get provider performance stats: {e}")
            return {}

    def bulk_update_model_status(self, model_ids: List[int], status: bool) -> int:
        """批量更新模型状态 - 使用批量更新"""
        start_time = time.time()

        try:
            with self.get_session() as session:
                # 使用批量更新
                result = (
                    session.query(LLMModel)
                    .filter(LLMModel.id.in_(model_ids))
                    .update(
                        {"is_enabled": status, "updated_at": datetime.utcnow()},
                        synchronize_session=False,
                    )
                )

                session.commit()

                query_time = time.time() - start_time
                self._update_stats(query_time)

                return result

        except Exception as e:
            logger.error(f"Failed to bulk update model status: {e}")
            return 0

    def get_database_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        try:
            with self.get_session() as session:
                # 获取表大小信息
                sql = text(
                    """
                    SELECT 
                        schemaname,
                        tablename,
                        pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                        pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                    FROM pg_tables 
                    WHERE schemaname = 'public'
                    ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                """
                )

                result = session.execute(sql)
                table_sizes = []

                for row in result:
                    table_sizes.append(
                        {
                            "table": row.tablename,
                            "size": row.size,
                            "size_bytes": row.size_bytes,
                        }
                    )

                # 获取连接数信息
                conn_sql = text(
                    """
                    SELECT 
                        count(*) as active_connections,
                        count(*) filter (where state = 'active') as active_queries,
                        count(*) filter (where state = 'idle') as idle_connections
                    FROM pg_stat_activity 
                    WHERE datname = current_database()
                """
                )

                conn_result = session.execute(conn_sql)
                conn_stats = conn_result.first()

                return {
                    "table_sizes": table_sizes,
                    "connection_stats": {
                        "active_connections": conn_stats.active_connections,
                        "active_queries": conn_stats.active_queries,
                        "idle_connections": conn_stats.idle_connections,
                    },
                    "service_stats": self.stats,
                }

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def optimize_database(self):
        """数据库优化操作"""
        try:
            with self.get_session() as session:
                # 分析表统计信息
                session.execute(text("ANALYZE"))

                # 清理过期数据
                cleanup_sql = text(
                    """
                    DELETE FROM provider_performance_logs 
                    WHERE created_at < NOW() - INTERVAL '30 days'
                """
                )
                session.execute(cleanup_sql)

                # 清理缓存
                session.execute(text("DISCARD ALL"))

                session.commit()
                logger.info("Database optimization completed")

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")

    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        return {
            "query_stats": self.stats,
            "cache_efficiency": (
                self.stats["cache_hits"]
                / max(self.stats["cache_hits"] + self.stats["cache_misses"], 1)
            ),
            "slow_query_rate": (
                self.stats["slow_queries"] / max(self.stats["total_queries"], 1)
            ),
            "avg_query_time": self.stats["avg_query_time"],
        }
