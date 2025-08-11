from fastapi import APIRouter, HTTPException
from app.services.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import (
    LLMModelCreate,
    LLMProviderCreate,
    LLMModelProviderCreate,
    LLMModelProviderUpdate,
    LLMModelParamCreate,
)

# 获取日志器
logger = get_factory_logger()
db_router = APIRouter(prefix="/v1/db", tags=["数据库管理"])


@db_router.get("/models")
async def get_db_models():
    """获取数据库中的模型列表"""
    try:
        models = db_service.get_all_models()
        return {
            "models": [
                {
                    "id": model.id,
                    "name": model.name,
                    "type": model.llm_type,
                    "description": model.description,
                    "is_enabled": model.is_enabled,
                    "created_at": model.created_at,
                    "updated_at": model.updated_at,
                }
                for model in models
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库模型失败: {str(e)}")


@db_router.post("/models")
async def create_db_model(model_data: LLMModelCreate):
    """创建模型"""
    try:
        # 检查是否已存在相同名称的模型
        existing_model = db_service.get_model_by_name(model_data.name)

        if existing_model:
            raise HTTPException(
                status_code=400, detail=f"模型已存在: {model_data.name}"
            )

        model = db_service.create_model(model_data)
        return {
            "message": "模型创建成功",
            "id": model.id,
            "name": model.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建模型失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"创建模型失败: {str(e)}")


@db_router.get("/providers")
async def get_db_providers():
    """获取数据库中的提供商列表"""
    try:
        providers = db_service.get_all_providers()
        return {
            "providers": [
                {
                    "id": provider.id,
                    "name": provider.name,
                    "type": provider.provider_type,
                    "description": provider.description,
                    "is_enabled": provider.is_enabled,
                    "created_at": provider.created_at,
                    "updated_at": provider.updated_at,
                }
                for provider in providers
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取提供商列表失败: {str(e)}")


@db_router.post("/providers")
async def create_db_provider(provider_data: LLMProviderCreate):
    """创建数据库提供商"""
    try:
        # 检查是否已存在相同名称和类型的提供商
        existing_provider = db_service.get_provider_by_name_and_type(
            provider_data.name, provider_data.provider_type
        )

        if existing_provider:
            raise HTTPException(
                status_code=400,
                detail=f"提供商已存在: {provider_data.name} ({provider_data.provider_type})",
            )

        provider = db_service.create_provider(provider_data)
        return {
            "message": "提供商创建成功",
            "provider_id": provider.id,
            "provider_name": provider.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建提供商失败: {str(e)}")


@db_router.post("/model-providers")
async def create_db_model_provider(model_provider_data: LLMModelProviderCreate):
    """创建模型-提供商关联"""
    try:
        # 检查是否已存在相同的模型-提供商关联
        existing_mp = db_service.get_model_provider_by_ids(
            model_provider_data.llm_id, model_provider_data.provider_id
        )

        if existing_mp:
            raise HTTPException(
                status_code=400,
                detail=f"模型-提供商关联已存在: 模型ID {model_provider_data.llm_id}, 提供商ID {model_provider_data.provider_id}",
            )

        model_provider = db_service.create_model_provider(model_provider_data)
        return {"message": "模型-提供商关联创建成功", "id": model_provider.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"创建模型-提供商关联失败: {str(e)}"
        )


# 更新模型-提供商关联
@db_router.put("/model-providers/{model_provider_id}")
async def update_db_model_provider(
    model_provider_id: int, model_provider_data: LLMModelProviderUpdate
):
    """更新模型-提供商关联"""
    try:
        model_provider = db_service.update_model_provider(
            model_provider_id, model_provider_data
        )
        return {"message": "模型-提供商关联更新成功", "id": model_provider.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"更新模型-提供商关联失败: {str(e)}"
        )

@db_router.post("/model-params")
async def create_db_model_param(param_data: LLMModelParamCreate):
    """创建模型参数"""
    try:
        # 检查是否已存在相同的模型参数
        existing_param = db_service.get_model_param_by_key(
            param_data.llm_id,
            param_data.provider_id,
            param_data.param_key,
        )

        if existing_param:
            raise HTTPException(
                status_code=400,
                detail=f"模型参数已存在: 模型ID {param_data.llm_id}, 参数键 {param_data.param_key}",
            )

        param = db_service.create_model_param(param_data)
        return {"message": "模型参数创建成功", "param_id": param.param_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建模型参数失败: {str(e)}")
