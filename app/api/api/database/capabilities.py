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
