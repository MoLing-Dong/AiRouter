"""
数据库模型管理接口
"""

from fastapi import APIRouter, Path, HTTPException, Body
from pydantic import BaseModel
from typing import Optional, Any, List
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import LLMModelCreate, ApiResponse, LLMModelUpdate

logger = get_factory_logger()
models_router = APIRouter(prefix="/models", tags=["Database Models"])


# ==================== Data Models ====================


class ModelItemData(BaseModel):
    """模型数据项"""

    id: int
    name: str
    type: str
    description: Optional[str]
    is_enabled: bool
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class ModelsListData(BaseModel):
    """模型列表数据"""

    models: List[ModelItemData]
    total: Optional[int] = None


# ==================== API Endpoints ====================


@models_router.get("", response_model=ApiResponse[ModelsListData])
async def get_models() -> ApiResponse[ModelsListData]:
    """获取所有模型列表"""
    try:
        models = db_service.get_all_models()
        model_items = [
            ModelItemData(
                id=model.id,
                name=model.name,
                type=model.llm_type.value if model.llm_type else "PUBLIC",
                description=model.description,
                is_enabled=model.is_enabled,
                created_at=model.created_at,
                updated_at=model.updated_at,
            )
            for model in models
        ]
        return ApiResponse.success(
            data=ModelsListData(models=model_items, total=len(model_items)),
            message="获取模型列表成功",
        )
    except Exception as e:
        logger.error(f"Get models failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get models failed: {str(e)}")


@models_router.post("", response_model=ApiResponse[dict])
async def create_model(model_data: LLMModelCreate) -> ApiResponse[dict]:
    """创建模型"""
    try:
        # Check if model already exists
        existing_model = db_service.get_model_by_name(model_data.name)
        if existing_model:
            return ApiResponse.fail(message=f"Model already exists: {model_data.name}")

        model = db_service.create_model(model_data)

        # Prepare response data
        response_data = {
            "id": model.id,
            "name": model.name,
        }

        # If provider association was created, add provider info
        if model_data.provider_id:
            provider = db_service.get_provider_by_id(model_data.provider_id)
            if provider:
                response_data["provider_info"] = {
                    "provider_id": model_data.provider_id,
                    "provider_name": provider.name,
                    "weight": model_data.provider_weight or 10,
                    "is_preferred": model_data.is_provider_preferred or False,
                }

        # If capabilities associations were created, add capabilities info
        if model_data.capability_ids:
            from app.models import Capability

            session = db_service.get_session()
            capabilities = []
            for cap_id in model_data.capability_ids:
                capability = (
                    session.query(Capability).filter_by(capability_id=cap_id).first()
                )
                if capability:
                    capabilities.append(
                        {
                            "capability_id": capability.capability_id,
                            "capability_name": capability.capability_name,
                            "description": capability.description,
                        }
                    )
            session.close()
            if capabilities:
                response_data["capabilities"] = capabilities

        return ApiResponse.success(
            data=response_data, message="Model created successfully"
        )

    except Exception as e:
        logger.error(f"Create model failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Create model failed: {str(e)}")


@models_router.delete("/{model_id}", response_model=ApiResponse[dict])
async def delete_model(
    model_id: int = Path(..., gt=0, description="模型ID", example=1)
) -> ApiResponse[dict]:
    """删除指定的模型"""
    try:
        # 检查模型是否存在
        model = db_service.get_model_by_id(model_id)
        if not model:
            return ApiResponse.fail(message=f"模型不存在：ID {model_id}", code=404)

        # 执行删除
        result = db_service.delete_model(model_id)

        if result:
            return ApiResponse.success(
                data={"model_id": model_id, "model_name": model.name},
                message=f"模型 '{model.name}' 已成功删除",
            )
        else:
            return ApiResponse.fail(message="删除模型失败")

    except Exception as e:
        logger.error(f"删除模型失败 (ID: {model_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除模型时发生错误：{str(e)}")


@models_router.put("/{model_id}", response_model=ApiResponse[ModelItemData])
async def update_model(
    model_id: int = Path(..., gt=0, description="模型ID", example=1),
    model_data: LLMModelUpdate = Body(...),
) -> ApiResponse[ModelItemData]:
    """更新模型"""
    try:
        model = db_service.update_model(model_id, model_data)
        if not model:
            return ApiResponse.fail(
                message=f"模型不存在：ID {model_id}",
                code=404,
            )

        # 转换为返回格式
        model_item = ModelItemData(
            id=model.id,
            name=model.name,
            type=model.llm_type.value if model.llm_type else "PUBLIC",
            description=model.description,
            is_enabled=model.is_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

        return ApiResponse.success(data=model_item, message="模型更新成功")
    except Exception as e:
        logger.error(f"更新模型失败 (ID: {model_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"更新模型时发生错误：{str(e)}")
