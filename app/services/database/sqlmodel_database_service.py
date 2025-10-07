"""
SQLModel数据库服务 - 现代化的数据库操作服务
使用SQLModel提供类型安全和更好的性能
"""

from sqlmodel import create_engine, Session, select
from typing import List, Dict, Optional, Any, Sequence
from datetime import datetime
import time

from app.models.sqlmodel_models import (
    LLMModel,
    LLMProvider,
    LLMModelProvider,
    LLMProviderApiKey,
    ModelCreateRequest,
    ProviderCreateRequest,
    ModelProviderCreateRequest,
    ModelProviderUpdateRequest,
    LLMProviderApiKeyCreateRequest,
    HealthStatus,
    QueryBuilder,
    PerformanceMetrics,
)
from config.settings import settings
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class SQLModelDatabaseService:
    """基于SQLModel的数据库服务"""

    def __init__(self):
        # 创建SQLModel引擎
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=getattr(settings, "DB_POOL_SIZE", 10),
            max_overflow=getattr(settings, "DB_MAX_OVERFLOW", 20),
            pool_timeout=getattr(settings, "DB_POOL_TIMEOUT", 30),
            pool_recycle=getattr(settings, "DB_POOL_RECYCLE", 3600),
            echo=False,  # 关闭数据库查询日志
        )

    def get_session(self) -> Session:
        """获取数据库会话"""
        return Session(self.engine)

    def close(self) -> None:
        """关闭数据库引擎"""
        try:
            if self.engine:
                self.engine.dispose()
        except Exception as e:
            logger.error(f"Error closing database engine: {e}")

    # ==================== 模型操作 ====================

    def get_all_models(self, is_enabled: Optional[bool] = None) -> List[LLMModel]:
        """获取所有模型"""
        with self.get_session() as session:
            statement = select(LLMModel)
            if is_enabled is not None:
                statement = statement.where(LLMModel.is_enabled == is_enabled)

            statement = statement.order_by(LLMModel.name)
            result = session.exec(statement)
            return list(result.all())

    def get_model_by_name(
        self, model_name: str, is_enabled: Optional[bool] = None
    ) -> Optional[LLMModel]:
        """根据名称获取模型"""
        with self.get_session() as session:
            statement = select(LLMModel).where(LLMModel.name == model_name)
            if is_enabled is not None:
                statement = statement.where(LLMModel.is_enabled == is_enabled)

            result = session.exec(statement)
            return result.first()

    def get_model_by_id(self, model_id: int) -> Optional[LLMModel]:
        """根据ID获取模型"""
        with self.get_session() as session:
            return session.get(LLMModel, model_id)

    def create_model(self, model_data: ModelCreateRequest) -> LLMModel:
        """创建模型"""
        with self.get_session() as session:
            # 创建模型实例
            model = LLMModel(
                name=model_data.name,
                llm_type=model_data.llm_type,
                description=model_data.description,
                is_enabled=model_data.is_enabled,
            )

            session.add(model)
            session.commit()
            session.refresh(model)

            logger.info(f"Created model: {model.name}")
            return model

    def update_model(
        self, model_id: int, model_data: Dict[str, Any]
    ) -> Optional[LLMModel]:
        """更新模型"""
        with self.get_session() as session:
            model = session.get(LLMModel, model_id)
            if not model:
                return None

            # 更新字段
            for field, value in model_data.items():
                if hasattr(model, field):
                    setattr(model, field, value)

            model.updated_at = datetime.utcnow()
            session.add(model)
            session.commit()
            session.refresh(model)

            logger.info(f"Updated model: {model.name}")
            return model

    def delete_model(self, model_id: int) -> bool:
        """删除模型"""
        with self.get_session() as session:
            model = session.get(LLMModel, model_id)
            if not model:
                return False

            session.delete(model)
            session.commit()

            logger.info(f"Deleted model: {model.name}")
            return True

    # ==================== 提供商操作 ====================

    def get_all_providers(self, is_enabled: Optional[bool] = None) -> List[LLMProvider]:
        """获取所有提供商"""
        with self.get_session() as session:
            statement = select(LLMProvider)
            if is_enabled is not None:
                statement = statement.where(LLMProvider.is_enabled == is_enabled)

            statement = statement.order_by(LLMProvider.name)
            result = session.exec(statement)
            return list(result.all())

    def get_provider_by_name(self, provider_name: str) -> Optional[LLMProvider]:
        """根据名称获取提供商"""
        with self.get_session() as session:
            statement = select(LLMProvider).where(LLMProvider.name == provider_name)
            result = session.exec(statement)
            return result.first()

    def get_provider_by_id(self, provider_id: int) -> Optional[LLMProvider]:
        """根据ID获取提供商"""
        with self.get_session() as session:
            return session.get(LLMProvider, provider_id)

    def create_provider(self, provider_data: ProviderCreateRequest) -> LLMProvider:
        """创建提供商"""
        with self.get_session() as session:
            provider = LLMProvider(
                name=provider_data.name,
                provider_type=provider_data.provider_type,
                official_endpoint=provider_data.official_endpoint,
                description=provider_data.description,
                is_enabled=provider_data.is_enabled,
            )

            session.add(provider)
            session.commit()
            session.refresh(provider)

            logger.info(f"Created provider: {provider.name}")
            return provider

    # ==================== 模型-提供商关联操作 ====================

    def get_models_with_providers(
        self, is_enabled: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """获取模型及其提供商信息"""
        with self.get_session() as session:
            statement = (
                select(LLMModel, LLMProvider, LLMModelProvider)
                .join(LLMModelProvider, LLMModel.id == LLMModelProvider.llm_id)
                .join(LLMProvider, LLMProvider.id == LLMModelProvider.provider_id)
            )

            if is_enabled is not None:
                statement = statement.where(
                    LLMModel.is_enabled == is_enabled,
                    LLMModelProvider.is_enabled == is_enabled,
                )

            result = session.exec(statement)
            models_data = []

            for model, provider, model_provider in result:
                models_data.append(
                    {
                        "model": model,
                        "provider": provider,
                        "model_provider": model_provider,
                    }
                )

            return models_data

    def get_healthy_models(self) -> List[LLMModel]:
        """获取有健康提供商的模型"""
        with self.get_session() as session:
            statement = QueryBuilder.get_models_with_healthy_providers()
            result = session.exec(statement)
            return list(result.all())

    def create_model_provider_association(
        self,
        model_id: int,
        provider_id: int,
        association_data: ModelProviderCreateRequest,
    ) -> LLMModelProvider:
        """创建模型-提供商关联"""
        with self.get_session() as session:
            model_provider = LLMModelProvider(
                llm_id=model_id,
                provider_id=provider_id,
                weight=association_data.weight,
                priority=association_data.priority,
                is_enabled=association_data.is_enabled,
                is_preferred=association_data.is_preferred,
                health_status=association_data.health_status,
            )

            session.add(model_provider)
            session.commit()
            session.refresh(model_provider)

            logger.info(
                f"Created association: model_id={model_id}, provider_id={provider_id}"
            )
            return model_provider

    def update_model_provider_metrics(
        self, model_provider_id: int, metrics: Dict[str, Any]
    ) -> Optional[LLMModelProvider]:
        """更新模型-提供商性能指标"""
        with self.get_session() as session:
            model_provider = session.get(LLMModelProvider, model_provider_id)
            if not model_provider:
                return None

            # 更新指标
            for field, value in metrics.items():
                if hasattr(model_provider, field):
                    setattr(model_provider, field, value)

            model_provider.updated_at = datetime.utcnow()
            session.add(model_provider)
            session.commit()
            session.refresh(model_provider)

            return model_provider

    def batch_update_model_provider_metrics(
        self, updates: List[Dict[str, Any]]
    ) -> bool:
        """批量更新模型-提供商指标"""
        try:
            with self.get_session() as session:
                for update in updates:
                    model_provider_id = update.get("id")
                    if not model_provider_id:
                        continue

                    model_provider = session.get(LLMModelProvider, model_provider_id)
                    if not model_provider:
                        continue

                    # 更新字段
                    for field, value in update.items():
                        if field != "id" and hasattr(model_provider, field):
                            setattr(model_provider, field, value)

                    model_provider.updated_at = datetime.utcnow()
                    session.add(model_provider)

                session.commit()
                logger.info(f"Batch updated {len(updates)} model provider metrics")
                return True

        except Exception as e:
            logger.error(f"Failed to batch update metrics: {e}")
            return False

    # ==================== API密钥操作 ====================

    def get_api_keys_for_provider(
        self, provider_id: int, is_enabled: Optional[bool] = None
    ) -> List[LLMProviderApiKey]:
        """获取提供商的API密钥"""
        with self.get_session() as session:
            statement = select(LLMProviderApiKey).where(
                LLMProviderApiKey.provider_id == provider_id
            )
            if is_enabled is not None:
                statement = statement.where(LLMProviderApiKey.is_enabled == is_enabled)

            result = session.exec(statement)
            return list(result.all())

    def get_best_api_key(self, provider_id: int) -> Optional[LLMProviderApiKey]:
        """获取最佳API密钥（优先级最高且可用）"""
        with self.get_session() as session:
            statement = (
                select(LLMProviderApiKey)
                .where(
                    LLMProviderApiKey.provider_id == provider_id,
                    LLMProviderApiKey.is_enabled == True,
                )
                .order_by(
                    LLMProviderApiKey.is_preferred.desc(),
                    LLMProviderApiKey.weight.desc(),
                )
            )

            result = session.exec(statement)
            return result.first()

    # ==================== 查询优化 ====================

    def get_model_config_from_db(self, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型配置"""
        with self.get_session() as session:
            # 获取模型信息
            model = self.get_model_by_name(model_name, is_enabled=True)
            if not model:
                return None

            # 获取关联的提供商
            statement = (
                select(LLMProvider, LLMModelProvider, LLMProviderApiKey)
                .join(LLMModelProvider, LLMProvider.id == LLMModelProvider.provider_id)
                .join(
                    LLMProviderApiKey, LLMProvider.id == LLMProviderApiKey.provider_id
                )
                .where(
                    LLMModelProvider.llm_id == model.id,
                    LLMModelProvider.is_enabled == True,
                    LLMProvider.is_enabled == True,
                    LLMProviderApiKey.is_enabled == True,
                )
                .order_by(
                    LLMModelProvider.priority.desc(), LLMModelProvider.weight.desc()
                )
            )

            result = session.exec(statement)
            providers = []

            for provider, model_provider, api_key in result:
                provider_config = {
                    "name": provider.name,
                    "base_url": provider.official_endpoint,
                    "api_key": api_key.api_key,
                    "model": model_name,
                    "weight": model_provider.weight,
                    "enabled": model_provider.is_enabled,
                    "is_preferred": model_provider.is_preferred,
                }
                providers.append(provider_config)

            return {
                "name": model_name,
                "providers": providers,
                "model_type": "chat",
                "enabled": model.is_enabled,
                "updated_at": model.updated_at,
            }

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模型配置"""
        models = self.get_all_models(is_enabled=True)
        configs = {}

        for model in models:
            config = self.get_model_config_from_db(model.name)
            if config:
                configs[model.name] = config

        return configs

    # ==================== 统计和监控 ====================

    def get_database_statistics(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self.get_session() as session:
            # 统计各表的记录数
            models_count = len(session.exec(select(LLMModel)).all())
            providers_count = len(session.exec(select(LLMProvider)).all())
            associations_count = len(session.exec(select(LLMModelProvider)).all())
            api_keys_count = len(session.exec(select(LLMProviderApiKey)).all())

            # 统计健康状态
            healthy_count = len(
                session.exec(
                    select(LLMModelProvider).where(
                        LLMModelProvider.health_status == HealthStatus.healthy
                    )
                ).all()
            )

            return {
                "models_count": models_count,
                "providers_count": providers_count,
                "associations_count": associations_count,
                "api_keys_count": api_keys_count,
                "healthy_associations": healthy_count,
                "timestamp": datetime.utcnow().isoformat(),
            }

    def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        try:
            with self.get_session() as session:
                # 测试基本查询
                session.exec(select(LLMModel).limit(1))

                return {
                    "status": "healthy",
                    "database": "postgresql",
                    "connection": "ok",
                    "timestamp": datetime.utcnow().isoformat(),
                }

        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# 全局实例
sqlmodel_db_service = SQLModelDatabaseService()
