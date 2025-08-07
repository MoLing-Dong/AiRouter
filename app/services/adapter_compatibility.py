from typing import Optional
from app.services.adapter_manager import ModelAdapterManager
from app.core.adapters.base import BaseAdapter, ChatRequest, ChatResponse
from config.settings import ModelConfig

# 全局适配器管理器实例
adapter_manager = ModelAdapterManager()


def get_adapter(model_name: str) -> Optional[BaseAdapter]:
    """获取模型的最佳适配器（兼容性函数）"""
    return adapter_manager.get_best_adapter(model_name)


def register_model(model_name: str, model_config: ModelConfig):
    """注册模型配置（兼容性函数）"""
    adapter_manager.register_model(model_name, model_config)


async def chat_completion(model_name: str, request: ChatRequest) -> ChatResponse:
    """执行聊天完成（兼容性函数）"""
    adapter = get_adapter(model_name)
    if not adapter:
        raise ValueError(f"没有可用的适配器: {model_name}")
    return await adapter.chat_completion(request)


def get_available_models() -> list:
    """获取所有可用模型（兼容性函数）"""
    return adapter_manager.get_available_models()


def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """获取模型配置（兼容性函数）"""
    return adapter_manager.get_model_config(model_name)


async def health_check_model(model_name: str) -> dict:
    """检查模型健康状态（兼容性函数）"""
    return await adapter_manager.health_check_model(model_name)


async def health_check_all() -> dict:
    """检查所有模型健康状态（兼容性函数）"""
    return await adapter_manager.health_check_all()


def refresh_from_database():
    """从数据库刷新模型配置（兼容性函数）"""
    adapter_manager.refresh_from_database()


def set_use_database(use_db: bool):
    """设置是否使用数据库配置（兼容性函数）"""
    adapter_manager.set_use_database(use_db)
