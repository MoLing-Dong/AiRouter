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
    """Model data item"""

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
    """Model list data"""

    models: List[ModelItemData]
    total: Optional[int] = None


# ==================== API Endpoints ====================


@models_router.get("", response_model=ApiResponse[ModelsListData])
async def get_models() -> ApiResponse[ModelsListData]:
    """Get all models list"""
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
            message="Get models list successfully",
        )
    except Exception as e:
        logger.error(f"Get models failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get models failed: {str(e)}")


@models_router.post("", response_model=ApiResponse[dict])
async def create_model(model_data: LLMModelCreate) -> ApiResponse[dict]:
    """Create model"""
    try:
        # Check if model already exists
        existing_model = db_service.get_model_by_name(model_data.name)
        if existing_model:
            return ApiResponse.fail(message=f"Model already exists: {model_data.name}", code=400)

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
    """Delete model"""
    try:
        # Check if model exists
        model = db_service.get_model_by_id(model_id)
        if not model:
            return ApiResponse.fail(message=f"Model not found: ID {model_id}", code=404)

        # Delete model
        result = db_service.delete_model(model_id)

        if result:
            return ApiResponse.success(
                data={"model_id": model_id, "model_name": model.name},
                message=f"Model '{model.name}' deleted successfully",
            )
        else:
            return ApiResponse.fail(message="Failed to delete model")

    except Exception as e:
        logger.error(f"Failed to delete model (ID: {model_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete model: {str(e)}")


@models_router.put("/{model_id}", response_model=ApiResponse[ModelItemData])
async def update_model(
    model_id: int = Path(..., gt=0, description="Model ID", example=1),
    model_data: LLMModelUpdate = Body(...),
) -> ApiResponse[ModelItemData]:
    """Update model"""
    try:
        model = db_service.update_model(model_id, model_data)
        if not model:
            return ApiResponse.fail(
                message=f"Model not found: ID {model_id}",
                code=404,
            )

        # Convert to return format
        model_item = ModelItemData(
            id=model.id,
            name=model.name,
            type=model.llm_type.value if model.llm_type else "PUBLIC",
            description=model.description,
            is_enabled=model.is_enabled,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

        return ApiResponse.success(
            data=model_item, message="Model updated successfully"
        )
    except Exception as e:
        logger.error(f"Failed to update model (ID: {model_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update model: {str(e)}")

