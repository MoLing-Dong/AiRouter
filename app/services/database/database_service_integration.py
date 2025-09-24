"""
数据库服务集成 - 整合同步和异步数据库服务
为了保持向后兼容性，同时提供新的异步功能
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime

from .database_service import db_service as sync_db_service
from .async_database_service import async_db_service
from ..monitoring.enhanced_model_service import enhanced_model_service
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class IntegratedDatabaseService:
    """
    集成数据库服务 - 提供同步和异步接口
    优先使用异步服务获得更好的性能，同时保持同步接口兼容性
    """

    def __init__(self):
        self.sync_service = sync_db_service
        self.async_service = async_db_service
        self.enhanced_service = enhanced_model_service
        self._async_initialized = False

    async def initialize_async(self):
        """初始化异步服务"""
        if not self._async_initialized:
            await self.enhanced_service.initialize()
            self._async_initialized = True
            logger.info("✅ Integrated database service initialized")

    async def close_async(self):
        """关闭异步服务"""
        if self._async_initialized:
            await self.enhanced_service.close()
            self._async_initialized = False

    # ==================== 模型查询接口 ====================

    def get_all_models(self, is_enabled: Optional[bool] = None) -> List[Any]:
        """
        同步接口：获取所有模型
        """
        return self.sync_service.get_all_models(is_enabled)

    async def get_all_models_async(
        self, 
        is_enabled: Optional[bool] = None,
        use_enhanced: bool = True
    ) -> List[Dict[str, Any]]:
        """
        异步接口：获取所有模型（推荐使用）
        """
        if use_enhanced and self._async_initialized:
            return await self.enhanced_service.get_all_models_enhanced(
                is_enabled=is_enabled,
                include_relationships=True,
                use_cache=True
            )
        else:
            return await self.async_service.get_all_models_with_relationships(is_enabled)

    def get_model_by_name(self, model_name: str, is_enabled: bool = None):
        """
        同步接口：根据名称获取模型
        """
        return self.sync_service.get_model_by_name(model_name, is_enabled)

    async def get_model_by_name_async(
        self, 
        model_name: str, 
        use_enhanced: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        异步接口：根据名称获取模型（推荐使用）
        """
        if use_enhanced and self._async_initialized:
            return await self.enhanced_service.get_model_by_name_enhanced(
                model_name=model_name,
                include_relationships=True,
                use_cache=True
            )
        else:
            return await self.async_service.get_model_by_name_optimized(model_name)

    def get_model_config_from_db(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        同步接口：获取模型配置
        """
        return self.sync_service.get_model_config_from_db(model_name)

    async def get_model_config_async(self, model_name: str) -> Optional[Dict[str, Any]]:
        """
        异步接口：获取模型配置
        """
        model_data = await self.get_model_by_name_async(model_name)
        if not model_data:
            return None

        # 转换为配置格式
        providers = []
        for provider_info in model_data.get("providers", []):
            if not provider_info.get("is_enabled"):
                continue

            # 获取API密钥（这里需要异步实现）
            # 暂时使用同步服务的方法
            provider = self.sync_service.get_provider_by_id(provider_info["provider_id"])
            if not provider:
                continue

            api_key_obj = self.sync_service.get_best_api_key(provider.id)
            if not api_key_obj:
                continue

            provider_config = {
                "name": provider_info.get("provider_name"),
                "base_url": provider.official_endpoint or provider.third_party_endpoint,
                "api_key": api_key_obj.api_key,
                "model": model_name,
                "weight": provider_info.get("weight", 10),
                "enabled": provider_info.get("is_enabled", True),
                "is_preferred": provider_info.get("is_preferred", False),
            }
            providers.append(provider_config)

        return {
            "name": model_name,
            "providers": providers,
            "model_type": "chat",
            "enabled": model_data.get("is_enabled", True),
            "updated_at": model_data.get("updated_at"),
        }

    # ==================== 性能分析接口 ====================

    async def get_model_performance_analysis_async(
        self, 
        model_name: str, 
        days: int = 7
    ) -> Optional[Dict[str, Any]]:
        """
        异步接口：获取模型性能分析
        """
        if self._async_initialized:
            return await self.enhanced_service.get_model_performance_analysis(
                model_name, days
            )
        return None

    async def get_provider_performance_summary_async(
        self, 
        days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        异步接口：获取提供商性能汇总
        """
        if self._async_initialized:
            return await self.enhanced_service.get_provider_performance_summary(days)
        return []

    async def get_healthy_models_async(self) -> List[Dict[str, Any]]:
        """
        异步接口：获取健康的模型
        """
        if self._async_initialized:
            return await self.enhanced_service.get_healthy_models()
        return []

    # ==================== 批量操作接口 ====================

    async def batch_update_metrics_async(
        self, 
        updates: List[Dict[str, Any]]
    ) -> bool:
        """
        异步接口：批量更新指标
        """
        if self._async_initialized:
            return await self.enhanced_service.batch_update_model_metrics(updates)
        
        # 回退到异步数据库服务
        return await self.async_service.batch_update_model_provider_metrics(updates)

    async def batch_health_check_async(
        self, 
        model_provider_pairs: List[tuple]
    ) -> Dict[str, Any]:
        """
        异步接口：批量健康检查
        """
        if self._async_initialized:
            return await self.enhanced_service.batch_health_check(model_provider_pairs)
        return {"error": "Enhanced service not initialized"}

    # ==================== 缓存管理接口 ====================

    async def clear_cache_async(self):
        """
        异步接口：清理缓存
        """
        if self._async_initialized:
            await self.enhanced_service.clear_all_cache()
        await self.async_service.clear_cache()

    async def get_service_statistics_async(self) -> Dict[str, Any]:
        """
        异步接口：获取服务统计
        """
        if self._async_initialized:
            return await self.enhanced_service.get_service_statistics()
        
        # 回退到异步数据库服务
        return await self.async_service.get_database_statistics()

    # ==================== 兼容性接口 ====================

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """
        同步接口：获取所有模型配置（兼容性）
        """
        return self.sync_service.get_all_model_configs_from_db()

    async def get_all_model_configs_async(self) -> Dict[str, Dict[str, Any]]:
        """
        异步接口：获取所有模型配置
        """
        models = await self.get_all_models_async(is_enabled=True)
        configs = {}
        
        # 并发获取所有模型配置
        tasks = []
        for model in models:
            task = self.get_model_config_async(model["name"])
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Failed to get config for model {models[i]['name']}: {result}")
                continue
            
            if result:
                configs[models[i]["name"]] = result
        
        return configs

    # ==================== 健康检查接口 ====================

    def health_check(self) -> Dict[str, Any]:
        """
        同步健康检查
        """
        try:
            # 测试同步数据库连接
            with self.sync_service.get_session() as session:
                session.execute("SELECT 1")
            
            return {
                "status": "healthy",
                "sync_db": "ok",
                "async_db": "ok" if self._async_initialized else "not_initialized",
                "enhanced_service": "ok" if self._async_initialized else "not_initialized",
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def health_check_async(self) -> Dict[str, Any]:
        """
        异步健康检查
        """
        try:
            # 测试异步数据库连接
            async with self.async_service.get_session() as session:
                await session.execute("SELECT 1")
            
            # 获取详细统计
            stats = await self.get_service_statistics_async()
            
            return {
                "status": "healthy",
                "sync_db": "ok",
                "async_db": "ok",
                "enhanced_service": "ok" if self._async_initialized else "not_initialized",
                "cache_enabled": self.enhanced_service.cache_enabled if self._async_initialized else False,
                "statistics": stats,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    # ==================== 便捷方法 ====================

    def run_async(self, coro):
        """
        在同步环境中运行异步代码的便捷方法
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已有事件循环在运行，创建任务
                task = asyncio.create_task(coro)
                return task
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(coro)


# 全局集成数据库服务实例
integrated_db_service = IntegratedDatabaseService()

# 为了向后兼容，导出为原始名称
db_service_integrated = integrated_db_service
