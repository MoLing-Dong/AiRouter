from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import List, Dict, Optional, Any
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
    LLMModelParamCreate,
    LLMProviderApiKeyCreate,
)
from config.settings import settings


class DatabaseService:
    """数据库服务"""

    def __init__(self):
        # PostgreSQL
        self.engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=settings.DEBUG,
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # 创建表
        Base.metadata.create_all(bind=self.engine)

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def get_all_models(self) -> List[LLMModel]:
        """获取所有启用的模型"""
        with self.get_session() as session:
            return session.query(LLMModel).filter(LLMModel.is_enabled == True).all()

    def get_model_by_name(self, model_name: str) -> Optional[LLMModel]:
        """根据模型名称获取模型"""
        with self.get_session() as session:
            return (
                session.query(LLMModel)
                .filter(LLMModel.name == model_name, LLMModel.is_enabled == True)
                .first()
            )

    def get_model_providers(self, model_id: int) -> List[LLMModelProvider]:
        """获取模型的所有提供商"""
        with self.get_session() as session:
            return (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.is_enabled == True,
                )
                .order_by(LLMModelProvider.weight.desc())
                .all()
            )

    def get_model_provider_by_ids(
        self, model_id: int, provider_id: int
    ) -> Optional[LLMModelProvider]:
        """根据模型ID和提供商ID获取模型-提供商关联"""
        with self.get_session() as session:
            return (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model_id,
                    LLMModelProvider.provider_id == provider_id,
                )
                .first()
            )

    def get_model_params(
        self, model_id: int, provider_id: Optional[int] = None
    ) -> List[LLMModelParam]:
        """获取模型参数"""
        with self.get_session() as session:
            query = session.query(LLMModelParam).filter(
                LLMModelParam.llm_id == model_id, LLMModelParam.is_enabled == True
            )

            if provider_id is not None:
                query = query.filter(LLMModelParam.provider_id == provider_id)

            return query.all()

    def get_model_param_by_key(
        self, model_id: int, provider_id: Optional[int], param_key: str
    ) -> Optional[LLMModelParam]:
        """根据模型ID、提供商ID和参数键获取模型参数"""
        with self.get_session() as session:
            query = session.query(LLMModelParam).filter(
                LLMModelParam.llm_id == model_id,
                LLMModelParam.param_key == param_key,
                LLMModelParam.is_enabled == True,
            )

            if provider_id is not None:
                query = query.filter(LLMModelParam.provider_id == provider_id)

            return query.first()

    def get_provider_by_id(self, provider_id: int) -> Optional[LLMProvider]:
        """根据ID获取提供商"""
        with self.get_session() as session:
            return (
                session.query(LLMProvider)
                .filter(LLMProvider.id == provider_id, LLMProvider.is_enabled == True)
                .first()
            )

    def get_provider_api_keys(self, provider_id: int) -> List[LLMProviderApiKey]:
        """获取提供商的所有API密钥"""
        with self.get_session() as session:
            return (
                session.query(LLMProviderApiKey)
                .filter(
                    LLMProviderApiKey.provider_id == provider_id,
                    LLMProviderApiKey.is_enabled == True,
                )
                .order_by(LLMProviderApiKey.weight.desc())
                .all()
            )

    def get_best_api_key(self, provider_id: int) -> Optional[LLMProviderApiKey]:
        """获取最佳API密钥（基于权重和偏好）"""
        api_keys = self.get_provider_api_keys(provider_id)
        if not api_keys:
            return None

        # 优先选择首选密钥
        preferred_keys = [key for key in api_keys if key.is_preferred]
        if preferred_keys:
            # 按权重排序
            preferred_keys.sort(key=lambda x: x.weight, reverse=True)
            return preferred_keys[0]

        # 如果没有首选密钥，按权重排序
        api_keys.sort(key=lambda x: x.weight, reverse=True)
        return api_keys[0]

    def create_model(self, model_data: LLMModelCreate) -> LLMModel:
        """创建模型"""
        with self.get_session() as session:
            model = LLMModel(**model_data.dict())
            session.add(model)
            session.commit()
            session.refresh(model)
            return model

    def create_provider(self, provider_data: LLMProviderCreate) -> LLMProvider:
        """创建提供商"""
        with self.get_session() as session:
            provider = LLMProvider(**provider_data.dict())
            session.add(provider)
            session.commit()
            session.refresh(provider)
            return provider

    def create_provider_api_key(
        self, api_key_data: LLMProviderApiKeyCreate
    ) -> LLMProviderApiKey:
        """创建提供商API密钥"""
        with self.get_session() as session:
            api_key = LLMProviderApiKey(**api_key_data.dict())
            session.add(api_key)
            session.commit()
            session.refresh(api_key)
            return api_key

    def create_model_provider(
        self, model_provider_data: LLMModelProviderCreate
    ) -> LLMModelProvider:
        """创建模型-提供商关联"""
        with self.get_session() as session:
            model_provider = LLMModelProvider(**model_provider_data.dict())
            session.add(model_provider)
            session.commit()
            session.refresh(model_provider)
            return model_provider

    def create_model_param(self, param_data: LLMModelParamCreate) -> LLMModelParam:
        """创建模型参数"""
        with self.get_session() as session:
            param = LLMModelParam(**param_data.dict())
            session.add(param)
            session.commit()
            session.refresh(param)
            return param

    def get_model_config_from_db(self, model_name: str) -> Optional[Dict[str, Any]]:
        """从数据库获取模型配置"""
        model = self.get_model_by_name(model_name)
        if not model:
            return None

        # 获取模型的所有提供商
        model_providers = self.get_model_providers(model.id)
        providers = []

        for mp in model_providers:
            provider = self.get_provider_by_id(mp.provider_id)
            if not provider:
                continue

            # 获取最佳API密钥
            api_key_obj = self.get_best_api_key(provider.id)
            if not api_key_obj:
                print(f"警告: 提供商 {provider.name} 没有可用的API密钥")
                continue

            # 获取提供商参数
            provider_params = self.get_model_params(model.id, provider.id)
            params = {}
            for param in provider_params:
                # 处理JSON格式的参数值
                if isinstance(param.param_value, dict):
                    params[param.param_key] = param.param_value
                else:
                    params[param.param_key] = param.param_value

            # 获取通用参数
            general_params = self.get_model_params(model.id, None)
            for param in general_params:
                if param.param_key not in params:
                    if isinstance(param.param_value, dict):
                        params[param.param_key] = param.param_value
                    else:
                        params[param.param_key] = param.param_value

            # 构建提供商配置
            provider_config = {
                "name": provider.name,
                "base_url": provider.official_endpoint or provider.third_party_endpoint,
                "api_key": api_key_obj.api_key,
                "weight": mp.weight,
                "max_tokens": int(params.get("max_tokens", 4096)),
                "temperature": float(params.get("temperature", 0.7)),
                "cost_per_1k_tokens": float(params.get("cost_per_1k_tokens", 0.0)),
                "timeout": int(params.get("timeout", 30)),
                "retry_count": int(params.get("retry_count", 3)),
                "enabled": mp.is_enabled,
                "is_preferred": mp.is_preferred,
                "api_key_name": api_key_obj.name,
                "api_key_weight": api_key_obj.weight,
            }

            providers.append(provider_config)

        # 构建模型配置
        model_config = {
            "name": model.name,
            "providers": providers,
            "model_type": "chat",  # 默认类型
            "max_tokens": 4096,
            "temperature": 0.7,
            "top_p": 1.0,
            "frequency_penalty": 0.0,
            "presence_penalty": 0.0,
            "enabled": model.is_enabled,
            "priority": 0,
        }

        return model_config

    def get_all_model_configs_from_db(self) -> Dict[str, Dict[str, Any]]:
        """从数据库获取所有模型配置"""
        models = self.get_all_models()
        configs = {}

        for model in models:
            config = self.get_model_config_from_db(model.name)
            if config:
                configs[model.name] = config

        return configs

    def update_model_enabled_status(self, model_name: str, enabled: bool) -> bool:
        """更新模型启用状态"""
        with self.get_session() as session:
            model = session.query(LLMModel).filter(LLMModel.name == model_name).first()
            if model:
                model.is_enabled = enabled
                session.commit()
                return True
            return False

    def update_provider_weight(
        self, model_name: str, provider_name: str, weight: int
    ) -> bool:
        """更新提供商权重"""
        with self.get_session() as session:
            model = session.query(LLMModel).filter(LLMModel.name == model_name).first()
            if not model:
                return False

            provider = (
                session.query(LLMProvider)
                .filter(LLMProvider.name == provider_name)
                .first()
            )
            if not provider:
                return False

            model_provider = (
                session.query(LLMModelProvider)
                .filter(
                    LLMModelProvider.llm_id == model.id,
                    LLMModelprovider.id == provider.id,
                )
                .first()
            )

            if model_provider:
                model_provider.weight = weight
                session.commit()
                return True
            return False

    def get_all_providers(self) -> List[LLMProvider]:
        """获取所有提供商"""
        with self.get_session() as session:
            return (
                session.query(LLMProvider).filter(LLMProvider.is_enabled == True).all()
            )

    def get_provider_by_name(self, provider_name: str) -> Optional[LLMProvider]:
        """根据名称获取提供商"""
        with self.get_session() as session:
            return (
                session.query(LLMProvider)
                .filter(LLMProvider.name == provider_name)
                .first()
            )

    def get_provider_by_name_and_type(
        self, provider_name: str, provider_type: str
    ) -> Optional[LLMProvider]:
        """根据名称和类型获取提供商"""
        with self.get_session() as session:
            return (
                session.query(LLMProvider)
                .filter(
                    LLMProvider.name == provider_name,
                    LLMProvider.provider_type == provider_type,
                )
                .first()
            )

    def update_api_key_usage(self, apikey_id: int, usage_count: int = None) -> bool:
        """更新API密钥使用次数"""
        with self.get_session() as session:
            api_key = (
                session.query(LLMProviderApiKey)
                .filter(LLMProviderApiKey.id == apikey_id)
                .first()
            )
            if api_key:
                if usage_count is not None:
                    api_key.usage_count = usage_count
                else:
                    api_key.usage_count += 1
                session.commit()
                return True
            return False


# 全局数据库服务实例
db_service = DatabaseService()
