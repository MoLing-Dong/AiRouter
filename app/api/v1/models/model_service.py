"""
模型查询服务模块
提供高效的模型数据查询和构建功能
"""

import time
from typing import Dict, List, Any, Optional
from app.services import adapter_manager
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ModelQueryService:
    """模型查询服务"""

    def __init__(self):
        """初始化模型查询服务"""
        self._is_initialized = False
        self._preload_task = None

    async def preload_models_cache(self):
        """异步预加载模型缓存，在应用启动时调用"""
        if self._is_initialized:
            return

        try:
            logger.info("🚀 Preloading models cache...")
            start_time = time.time()

            # 预加载所有模型数据
            all_models = db_service.get_all_models(is_enabled=True)
            if not all_models:
                logger.warning("No enabled models found for preloading")
                return

            # 预加载capabilities
            all_capabilities = self._get_all_models_capabilities_batch(all_models)

            # 获取可用模型
            available_models = self._get_available_models_fast()

            # 构建模型列表
            models = []
            for model_name in available_models:
                try:
                    model_data = self._build_model_data(
                        model_name, all_models, all_capabilities
                    )
                    if model_data:
                        models.append(model_data)
                except Exception as e:
                    logger.warning(f"Error building model data for {model_name}: {e}")
                    continue

            # 预热缓存
            from .cache_manager import models_cache

            response_data = {"object": "list", "data": models}
            models_cache.prewarm_cache(response_data)

            preload_time = time.time() - start_time
            logger.info(
                f"✅ Models cache preloaded in {preload_time:.3f}s with {len(models)} models"
            )
            self._is_initialized = True

        except Exception as e:
            logger.error(f"Failed to preload models cache: {e}")

    def get_models_with_capabilities(
        self, capabilities: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        获取模型列表，支持能力过滤

        Args:
            capabilities: 能力过滤列表，None表示不过滤

        Returns:
            模型列表
        """
        start_time = time.time()

        try:
            # 性能优化1: 批量获取所有模型配置，避免N+1查询
            all_models = db_service.get_all_models(is_enabled=True)
            if not all_models:
                logger.warning("No enabled models found in database")
                return []

            # 性能优化2: 批量获取所有模型的capabilities
            all_capabilities = self._get_all_models_capabilities_batch(all_models)

            # 性能优化3: 从adapter_manager获取可用模型
            available_models = self._get_available_models_fast()

            # 构建模型列表
            models = []
            for model_name in available_models:
                try:
                    model_data = self._build_model_data(
                        model_name, all_models, all_capabilities
                    )
                    if model_data:
                        models.append(model_data)
                except Exception as e:
                    logger.warning(f"Error building model data for {model_name}: {e}")
                    continue

            response_time = time.time() - start_time
            logger.info(
                f"✅ Models list generated in {response_time:.3f}s, "
                f"returned {len(models)} models"
            )

            return models

        except Exception as e:
            logger.error(f"Failed to get models with capabilities: {e}")
            raise

    def _get_all_models_capabilities_batch(
        self, models: List[Any]
    ) -> Dict[int, List[Dict[str, Any]]]:
        """
        批量获取所有模型的能力信息

        Args:
            models: 模型对象列表

        Returns:
            模型ID到能力列表的映射
        """
        try:
            model_ids = [model.id for model in models]
            return db_service.get_all_models_capabilities_batch(model_ids)
        except Exception as e:
            logger.warning(f"Failed to get batch capabilities: {e}")
            return {}

    def _get_available_models_fast(self) -> List[str]:
        """
        快速获取可用模型列表

        Returns:
            可用模型名称列表
        """
        try:
            # 使用快速方法，跳过版本检查
            if hasattr(adapter_manager, "get_available_models_fast"):
                return adapter_manager.get_available_models_fast(
                    skip_version_check=True
                )
            else:
                # 降级到标准方法
                return adapter_manager.get_available_models()
        except Exception as e:
            logger.warning(f"Failed to get available models fast: {e}")
            return []

    def _build_model_data(
        self,
        model_name: str,
        all_models: List[Any],
        all_capabilities: Dict[int, List[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        """
        构建单个模型的数据

        Args:
            model_name: 模型名称
            all_models: 所有模型对象
            all_capabilities: 所有模型的能力映射

        Returns:
            模型数据字典，失败时返回None
        """
        try:
            # 获取模型适配器
            adapters = self._get_model_adapters_fast(model_name)
            if not adapters:
                return None

            # 获取模型对象
            model_obj = next((m for m in all_models if m.name == model_name), None)
            if not model_obj:
                return None

            # 获取能力信息
            capabilities = all_capabilities.get(model_obj.id, [])

            # 构建模型数据
            return {
                "id": model_name,
                "object": "model",
                "created": int(time.time()),
                "permission": [adapter.provider for adapter in adapters],
                "root": model_name,
                "parent": None,
                "providers_count": len(adapters),
                "capabilities": capabilities,
                "capabilities_count": len(capabilities),
            }

        except Exception as e:
            logger.warning(f"Error building model data for {model_name}: {e}")
            return None

    def _get_model_adapters_fast(self, model_name: str) -> List[Any]:
        """
        快速获取模型适配器

        Args:
            model_name: 模型名称

        Returns:
            适配器列表
        """
        try:
            # 使用快速方法，跳过版本检查
            if hasattr(adapter_manager, "get_model_adapters_fast"):
                return adapter_manager.get_model_adapters_fast(
                    model_name, skip_version_check=True
                )
            else:
                # 降级到标准方法
                return adapter_manager.get_model_adapters(model_name)
        except Exception as e:
            logger.warning(f"Failed to get adapters fast for {model_name}: {e}")
            return []


# 全局模型查询服务实例
model_service = ModelQueryService()
