"""
性能优化配置模块
提供数据库连接池、查询优化等性能提升配置
"""

from typing import Dict, Any
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class PerformanceConfig:
    """性能优化配置"""

    # 数据库连接池配置
    DB_POOL_SIZE = 20
    DB_MAX_OVERFLOW = 30
    DB_POOL_TIMEOUT = 30
    DB_POOL_RECYCLE = 3600

    # 缓存配置
    CACHE_TTL = 300  # 5分钟
    CACHE_MAX_SIZE = 1000

    # 查询优化配置
    QUERY_TIMEOUT = 10  # 查询超时时间（秒）
    MAX_RESULTS = 1000  # 最大结果数量

    # 异步配置
    ASYNC_PRELOAD = True
    ASYNC_BATCH_SIZE = 50

    @classmethod
    def get_db_config(cls) -> Dict[str, Any]:
        """获取数据库连接池配置"""
        return {
            "pool_size": cls.DB_POOL_SIZE,
            "max_overflow": cls.DB_MAX_OVERFLOW,
            "pool_timeout": cls.DB_POOL_TIMEOUT,
            "pool_recycle": cls.DB_POOL_RECYCLE,
        }

    @classmethod
    def get_cache_config(cls) -> Dict[str, Any]:
        """获取缓存配置"""
        return {
            "ttl": cls.CACHE_TTL,
            "max_size": cls.CACHE_MAX_SIZE,
        }

    @classmethod
    def log_performance_settings(cls):
        """记录性能配置信息"""
        logger.info("🚀 Performance optimization settings:")
        logger.info(f"   Database pool: {cls.get_db_config()}")
        logger.info(f"   Cache: {cls.get_cache_config()}")
        logger.info(f"   Async preload: {cls.ASYNC_PRELOAD}")
        logger.info(f"   Query timeout: {cls.QUERY_TIMEOUT}s")
        logger.info(f"   Max results: {cls.MAX_RESULTS}")


# 全局性能配置实例
performance_config = PerformanceConfig()
