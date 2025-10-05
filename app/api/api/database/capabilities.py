"""
数据库能力管理接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import ApiResponse

logger = get_factory_logger()
capabilities_router = APIRouter(prefix="/capabilities", tags=["Database Capabilities"])


# ==================== Data Models ====================


class CapabilityItemData(BaseModel):
    """能力数据项"""

    capability_id: int
    capability_name: str
    description: Optional[str]


class CapabilitiesListData(BaseModel):
    """能力列表数据"""

    capabilities: List[CapabilityItemData]
    total: Optional[int] = None


class CreateCapabilityRequest(BaseModel):
    """创建能力请求"""

    capability_name: str
    description: Optional[str] = None


class UpdateModelCapabilitiesRequest(BaseModel):
    """更新模型能力请求"""

    capability_ids: List[int]


# ==================== API Endpoints ====================


@capabilities_router.get("", response_model=ApiResponse[CapabilitiesListData])
async def get_capabilities() -> ApiResponse[CapabilitiesListData]:
    """获取所有能力列表"""
    try:
        from app.models import Capability

        session = db_service.get_session()
        capabilities = session.query(Capability).all()

        capability_items = [
            CapabilityItemData(
                capability_id=cap.capability_id,
                capability_name=cap.capability_name,
                description=cap.description,
            )
            for cap in capabilities
        ]

        session.close()
        return ApiResponse.success(
            data=CapabilitiesListData(
                capabilities=capability_items, total=len(capability_items)
            ),
            message="获取能力列表成功",
        )
    except Exception as e:
        logger.error(f"Get capabilities failed: {str(e)}")
        session.close()
        raise HTTPException(
            status_code=500, detail=f"Get capabilities failed: {str(e)}"
        )


@capabilities_router.post("", response_model=ApiResponse[dict])
async def create_capability(request: CreateCapabilityRequest) -> ApiResponse[dict]:
    """创建新能力"""
    try:
        from app.models import Capability

        session = db_service.get_session()

        # Check if capability already exists
        existing = (
            session.query(Capability)
            .filter_by(capability_name=request.capability_name.upper())
            .first()
        )
        if existing:
            session.close()
            return ApiResponse.fail(
                message=f"Capability already exists: {request.capability_name}"
            )

        # Create new capability
        capability = Capability(
            capability_name=request.capability_name.upper(),
            description=request.description,
        )
        session.add(capability)
        session.commit()

        result_data = {
            "capability_id": capability.capability_id,
            "capability_name": capability.capability_name,
            "description": capability.description,
        }

        session.close()
        return ApiResponse.success(
            data=result_data, message="Capability created successfully"
        )
    except Exception as e:
        logger.error(f"Create capability failed: {str(e)}")
        session.close()
        raise HTTPException(
            status_code=500, detail=f"Create capability failed: {str(e)}"
        )


@capabilities_router.delete("/{capability_id}", response_model=ApiResponse[dict])
async def delete_capability(capability_id: int) -> ApiResponse[dict]:
    """Delete capability"""
    try:
        from app.models import Capability

        session = db_service.get_session()

        capability = (
            session.query(Capability).filter_by(capability_id=capability_id).first()
        )
        if not capability:
            session.close()
            return ApiResponse.fail(message=f"Capability not found: {capability_id}")

        session.delete(capability)
        session.commit()

        result_data = {
            "capability_id": capability.capability_id,
            "capability_name": capability.capability_name,
            "description": capability.description,
        }

        session.close()
        return ApiResponse.success(
            data=result_data, message="Capability deleted successfully"
        )
    except Exception as e:
        logger.error(f"Failed to delete capability: {str(e)}")
        session.close()
        raise HTTPException(
            status_code=500, detail=f"Failed to delete capability: {str(e)}"
        )


@capabilities_router.get("/model/{model_id}", response_model=ApiResponse[list])
async def get_model_capabilities(model_id: int) -> ApiResponse[list]:
    """获取模型的所有能力"""
    try:
        from app.models import Capability, LLMModelCapability, LLMModel

        session = db_service.get_session()

        # 验证模型是否存在
        model = session.query(LLMModel).filter_by(id=model_id).first()
        if not model:
            session.close()
            return ApiResponse.fail(message=f"Model not found: {model_id}")

        # 通过关联表查询模型的能力
        capabilities = (
            session.query(Capability)
            .join(
                LLMModelCapability,
                Capability.capability_id == LLMModelCapability.capability_id,
            )
            .filter(LLMModelCapability.model_id == model_id)
            .all()
        )

        result_data = [
            {
                "capability_id": cap.capability_id,
                "capability_name": cap.capability_name,
                "description": cap.description,
            }
            for cap in capabilities
        ]

        session.close()
        return ApiResponse.success(
            data=result_data,
            message=f"Retrieved {len(result_data)} capabilities for model {model_id}",
        )
    except Exception as e:
        logger.error(f"Failed to get model capabilities: {str(e)}")
        if "session" in locals():
            session.close()
        raise HTTPException(
            status_code=500, detail=f"Failed to get model capabilities: {str(e)}"
        )


@capabilities_router.put(
    "/model/{model_id}/capabilities", response_model=ApiResponse[dict]
)
async def update_model_capabilities(
    model_id: int, request: UpdateModelCapabilitiesRequest
) -> ApiResponse[dict]:
    """Update model capabilities"""
    try:
        from app.models import Capability, LLMModelCapability, LLMModel

        session = db_service.get_session()

        # Verify if the model exists
        model = session.query(LLMModel).filter_by(id=model_id).first()
        if not model:
            session.close()
            return ApiResponse.fail(message=f"Model not found: {model_id}")

        # Verify if all capabilities exist
        capabilities = (
            session.query(Capability)
            .filter(Capability.capability_id.in_(request.capability_ids))
            .all()
        )
        if len(capabilities) != len(request.capability_ids):
            session.close()
            return ApiResponse.fail(message="Some capabilities not found")

        # Delete existing all associations
        deleted_count = (
            session.query(LLMModelCapability)
            .filter_by(model_id=model_id)
            .delete(synchronize_session=False)
        )

        # Add new associations
        for capability_id in request.capability_ids:
            model_capability = LLMModelCapability(
                model_id=model_id, capability_id=capability_id
            )
            session.add(model_capability)

        session.commit()

        result_data = {
            "model_id": model_id,
            "model_name": model.model_name,
            "removed_count": deleted_count,
            "added_count": len(request.capability_ids),
            "capability_ids": request.capability_ids,
        }

        session.close()
        return ApiResponse.success(
            data=result_data,
            message=f"Updated model capabilities: removed {deleted_count}, added {len(request.capability_ids)}",
        )
    except Exception as e:
        logger.error(f"Failed to update model capabilities: {str(e)}")
        if "session" in locals():
            session.rollback()
            session.close()
        raise HTTPException(
            status_code=500, detail=f"Failed to update model capabilities: {str(e)}"
        )
