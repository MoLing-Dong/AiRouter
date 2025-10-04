"""
数据库提供商管理接口
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any, List
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import LLMProviderCreate, ApiResponse

logger = get_factory_logger()
providers_router = APIRouter(prefix="/providers", tags=["Database Providers"])


# ==================== Data Models ====================


class ProviderItemData(BaseModel):
    """提供商数据项"""

    id: int
    name: str
    type: str
    description: Optional[str]
    is_enabled: bool
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class ProvidersListData(BaseModel):
    """提供商列表数据"""

    providers: List[ProviderItemData]
    total: Optional[int] = None


# ==================== API Endpoints ====================


@providers_router.get("", response_model=ApiResponse[ProvidersListData])
async def get_providers() -> ApiResponse[ProvidersListData]:
    """获取所有提供商列表"""
    try:
        providers = db_service.get_all_providers()
        provider_items = [
            ProviderItemData(
                id=provider.id,
                name=provider.name,
                type=(
                    provider.provider_type.value if provider.provider_type else "custom"
                ),
                description=provider.description,
                is_enabled=provider.is_enabled,
                created_at=provider.created_at,
                updated_at=provider.updated_at,
            )
            for provider in providers
        ]
        return ApiResponse.success(
            data=ProvidersListData(providers=provider_items, total=len(provider_items)),
            message="获取提供商列表成功",
        )
    except Exception as e:
        logger.error(f"Get providers failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Get providers failed: {str(e)}")


@providers_router.post("", response_model=ApiResponse[dict])
async def create_provider(provider_data: LLMProviderCreate) -> ApiResponse[dict]:
    """创建提供商"""
    try:
        # Check if provider already exists
        existing_provider = db_service.get_provider_by_name_and_type(
            provider_data.name, provider_data.provider_type
        )

        if existing_provider:
            return ApiResponse.fail(
                message=f"Provider already exists: {provider_data.name} ({provider_data.provider_type})",
            )

        provider = db_service.create_provider(provider_data)
        return ApiResponse.success(
            data={"provider_id": provider.id, "provider_name": provider.name},
            message="Provider created successfully",
        )
    except Exception as e:
        logger.error(f"Create provider failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Create provider failed: {str(e)}")
