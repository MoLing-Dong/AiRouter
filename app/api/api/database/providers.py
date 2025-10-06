"""
数据库提供商管理接口
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Any, List
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import LLMProviderCreate, ApiResponse, PaginatedResponse

logger = get_factory_logger()
providers_router = APIRouter(prefix="/providers", tags=["Database Providers"])


# ==================== Data Models ====================


class ProviderItemData(BaseModel):
    """提供商数据项"""

    id: int
    name: str
    type: str
    official_endpoint: Optional[str] = None
    description: Optional[str]
    is_enabled: bool
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class ProvidersPaginatedResponse(PaginatedResponse[ProviderItemData]):
    """提供商分页响应，将data字段序列化为providers"""

    data: List[ProviderItemData] = Field(
        description="提供商列表", serialization_alias="providers"
    )


# ==================== API Endpoints ====================


@providers_router.get("", response_model=ApiResponse[ProvidersPaginatedResponse])
async def get_providers(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    limit: int = Query(10, ge=1, le=100, description="每页数量（最大100）"),
    is_enabled: Optional[bool] = Query(None, description="是否启用筛选"),
) -> ApiResponse[ProvidersPaginatedResponse]:
    """获取提供商列表（支持分页）"""
    try:
        from app.models import LLMProvider
        from math import ceil

        session = db_service.get_session()

        try:
            # 创建查询
            query = session.query(LLMProvider)

            # 可选的筛选条件
            if is_enabled is not None:
                query = query.filter(LLMProvider.is_enabled == is_enabled)

            # 获取总数
            total = query.count()

            # 计算总页数
            total_pages = ceil(total / limit) if limit > 0 else 0

            # 排序并分页
            offset = (page - 1) * limit
            providers = (
                query.order_by(LLMProvider.id.desc()).offset(offset).limit(limit).all()
            )

            # 转换为响应格式
            provider_items = [
                ProviderItemData(
                    id=provider.id,
                    name=provider.name,
                    type=(
                        provider.provider_type.value
                        if provider.provider_type
                        else "custom"
                    ),
                    official_endpoint=provider.official_endpoint,
                    description=provider.description,
                    is_enabled=provider.is_enabled,
                    created_at=provider.created_at,
                    updated_at=provider.updated_at,
                )
                for provider in providers
            ]

            # 构建响应
            return ApiResponse.success(
                data=ProvidersPaginatedResponse(
                    data=provider_items,
                    total=total,
                    page=page,
                    page_size=limit,
                    total_pages=total_pages,
                    has_prev=page > 1,
                    has_next=page < total_pages,
                ),
                message=f"获取第 {page} 页数据成功，共 {total} 条记录",
            )

        finally:
            session.close()

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
