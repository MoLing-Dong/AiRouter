"""
模型缓存管理模块
提供模型列表的缓存功能，提升API响应性能
"""

import time
from typing import Dict, Any, Optional, Tuple
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ModelsCacheManager:
    """模型缓存管理器"""
    
    def __init__(self, ttl: int = 30):
        """
        初始化缓存管理器
        
        Args:
            ttl: 缓存生存时间（秒），默认30秒
        """
        self._models_cache: Dict[str, Any] = {}
        self._cache_timestamp: float = 0
        self._cache_ttl: int = ttl
        self._cache_hits: int = 0
        self._cache_misses: int = 0
    
    def get_cached_models(self) -> Tuple[Optional[Dict[str, Any]], bool]:
        """
        获取缓存的模型列表
        
        Returns:
            (cached_data, is_cached): 缓存数据和是否命中缓存的元组
        """
        current_time = time.time()
        
        if current_time - self._cache_timestamp < self._cache_ttl and self._models_cache:
            self._cache_hits += 1
            logger.debug(f"✅ Cache hit #{self._cache_hits}")
            return self._models_cache, True
        
        self._cache_misses += 1
        logger.debug(f"❌ Cache miss #{self._cache_misses}")
        return None, False
    
    def set_cached_models(self, models_data: Dict[str, Any]) -> None:
        """
        设置模型列表缓存
        
        Args:
            models_data: 要缓存的模型数据
        """
        self._models_cache = models_data
        self._cache_timestamp = time.time()
        logger.debug(f"💾 Cache updated with {len(models_data.get('data', []))} models")
    
    def clear_cache(self) -> None:
        """清理模型列表缓存"""
        self._models_cache = {}
        self._cache_timestamp = 0
        logger.info("🧹 Models cache cleared")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息字典
        """
        total_requests = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "total_requests": total_requests,
            "hit_rate": round(hit_rate, 2),
            "cache_size": len(self._models_cache),
            "last_update": self._cache_timestamp,
            "ttl": self._cache_ttl,
            "is_valid": time.time() - self._cache_timestamp < self._cache_ttl
        }
    
    def is_cache_valid(self) -> bool:
        """
        检查缓存是否有效
        
        Returns:
            缓存是否有效
        """
        return time.time() - self._cache_timestamp < self._cache_ttl


# 全局缓存管理器实例
models_cache = ModelsCacheManager()
