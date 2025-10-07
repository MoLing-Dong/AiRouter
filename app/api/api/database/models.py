"""
数据库模型管理接口
"""

from fastapi import APIRouter, Path, HTTPException, Body, Query
from pydantic import BaseModel, Field
from typing import Optional, Any, List
from contextlib import contextmanager
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import LLMModelCreate, ApiResponse, LLMModelUpdate, PaginatedResponse

logger = get_factory_logger()
models_router = APIRouter(prefix="/models", tags=["Database Models"])


# ==================== Data Models ====================


class ProviderInfo(BaseModel):
    """供应商信息"""

    id: int
    name: str
    provider_type: str
    weight: int
    is_preferred: bool
    health_status: str


class CapabilityInfo(BaseModel):
    """能力信息"""

    capability_id: int
    capability_name: str
    description: Optional[str]


class ModelItemData(BaseModel):
    """Model data item"""

    id: int
    name: str
    type: str
    description: Optional[str]
    is_enabled: bool
    providers: List[ProviderInfo] = []
    capabilities: List[CapabilityInfo] = []
    created_at: Any
    updated_at: Any

    class Config:
        from_attributes = True


class ModelsPaginatedResponse(PaginatedResponse[ModelItemData]):
    """模型分页响应，将data字段序列化为models"""

    data: List[ModelItemData] = Field(
        description="模型列表", serialization_alias="models"
    )


# ==================== Helper Functions ====================


@contextmanager
def get_db_session():
    """数据库会话上下文管理器"""
    session = db_service.get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def build_model_item_data(model) -> ModelItemData:
    """构建模型数据响应对象（避免代码重复）"""
    # 提取供应商信息
    providers_info = [
        ProviderInfo(
            id=mp.provider.id,
            name=mp.provider.name,
            provider_type=(
                mp.provider.provider_type.value
                if mp.provider.provider_type
                else "custom"
            ),
            weight=mp.weight,
            is_preferred=mp.is_preferred,
            health_status=(mp.health_status.value if mp.health_status else "unknown"),
        )
        for mp in model.providers
        if mp.provider
    ]

    # 提取能力信息
    capabilities_info = [
        CapabilityInfo(
            capability_id=mc.capability.capability_id,
            capability_name=mc.capability.capability_name,
            description=mc.capability.description,
        )
        for mc in model.capabilities
        if mc.capability
    ]

    return ModelItemData(
        id=model.id,
        name=model.name,
        type=model.llm_type.value if model.llm_type else "PUBLIC",
        description=model.description,
        is_enabled=model.is_enabled,
        providers=providers_info,
        capabilities=capabilities_info,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


# ==================== API Endpoints ====================


@models_router.get("", response_model=ApiResponse[ModelsPaginatedResponse])
async def get_models(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    limit: int = Query(10, ge=1, le=100, description="每页数量（最大100）"),
    is_enabled: Optional[bool] = Query(None, description="是否启用筛选启用模型"),
) -> ApiResponse[ModelsPaginatedResponse]:
    """
    Get models list
    """
    try:
        from app.models import LLMModel, LLMModelProvider, LLMModelCapability
        from sqlalchemy.orm import joinedload
        from math import ceil

        with get_db_session() as session:
            # 创建查询，使用 joinedload 进行关联加载
            query = session.query(LLMModel).options(
                joinedload(LLMModel.providers).joinedload(LLMModelProvider.provider),
                joinedload(LLMModel.capabilities).joinedload(
                    LLMModelCapability.capability
                ),
            )

            # 可选的筛选条件
            if is_enabled is not None:
                query = query.filter(LLMModel.is_enabled == is_enabled)

            # 获取总数
            total = query.count()

            # 计算总页数
            total_pages = ceil(total / limit) if limit > 0 else 0

            # 排序并分页
            offset = (page - 1) * limit
            models = (
                query.order_by(LLMModel.id.desc()).offset(offset).limit(limit).all()
            )

            # 转换为响应格式 - 使用辅助函数
            model_items = [build_model_item_data(model) for model in models]

            # 构建响应
            return ApiResponse.success(
                data=ModelsPaginatedResponse(
                    data=model_items,
                    total=total,
                    page=page,
                    page_size=limit,
                    total_pages=total_pages,
                    has_prev=page > 1,
                    has_next=page < total_pages,
                ),
                message=f"获取第 {page} 页数据成功，共 {total} 条记录",
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
            return ApiResponse.fail(
                message=f"Model already exists: {model_data.name}", code=400
            )

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
        from app.models import (
            LLMModel,
            LLMModelProvider,
            LLMModelCapability,
            Capability,
            LLMProvider,
        )
        from sqlalchemy.orm import joinedload

        # 提前验证能力是否存在（避免事务中途失败）
        if model_data.capability_ids is not None:
            with get_db_session() as session:
                existing_caps = (
                    session.query(Capability.capability_id)
                    .filter(Capability.capability_id.in_(model_data.capability_ids))
                    .all()
                )
                existing_cap_ids = {cap[0] for cap in existing_caps}
                invalid_caps = set(model_data.capability_ids) - existing_cap_ids
                if invalid_caps:
                    return ApiResponse.fail(
                        message=f"Invalid capability IDs: {sorted(invalid_caps)}",
                        code=400,
                    )

        with get_db_session() as session:
            # 获取模型（带关联加载）
            model = (
                session.query(LLMModel)
                .options(
                    joinedload(LLMModel.providers).joinedload(
                        LLMModelProvider.provider
                    ),
                    joinedload(LLMModel.capabilities).joinedload(
                        LLMModelCapability.capability
                    ),
                )
                .filter_by(id=model_id)
                .first()
            )

            if not model:
                return ApiResponse.fail(
                    message=f"Model not found: ID {model_id}",
                    code=404,
                )

            # 更新基本信息
            if model_data.name is not None:
                model.name = model_data.name
            if model_data.llm_type is not None:
                model.llm_type = model_data.llm_type
            if model_data.description is not None:
                model.description = model_data.description
            if model_data.is_enabled is not None:
                model.is_enabled = model_data.is_enabled

            # 优化：增量更新能力关联
            if model_data.capability_ids is not None:
                # 获取当前能力ID集合
                current_cap_ids = {mc.capability_id for mc in model.capabilities}
                new_cap_ids = set(model_data.capability_ids)

                # 删除不再需要的能力关联
                caps_to_remove = current_cap_ids - new_cap_ids
                if caps_to_remove:
                    session.query(LLMModelCapability).filter(
                        LLMModelCapability.model_id == model_id,
                        LLMModelCapability.capability_id.in_(caps_to_remove),
                    ).delete(synchronize_session=False)

                # 添加新的能力关联
                caps_to_add = new_cap_ids - current_cap_ids
                for cap_id in caps_to_add:
                    model_capability = LLMModelCapability(
                        model_id=model_id, capability_id=cap_id
                    )
                    session.add(model_capability)

            # 更新提供商关联
            if model_data.provider_id is not None:
                # 检查提供商是否存在
                provider = (
                    session.query(LLMProvider)
                    .filter_by(id=model_data.provider_id)
                    .first()
                )
                if not provider:
                    return ApiResponse.fail(
                        message=f"Provider not found: ID {model_data.provider_id}",
                        code=404,
                    )

                # 检查是否已存在该关联
                existing_relation = (
                    session.query(LLMModelProvider)
                    .filter_by(llm_id=model_id, provider_id=model_data.provider_id)
                    .first()
                )

                if existing_relation:
                    # 更新现有关联
                    if model_data.provider_weight is not None:
                        existing_relation.weight = model_data.provider_weight
                    if model_data.is_provider_preferred is not None:
                        existing_relation.is_preferred = (
                            model_data.is_provider_preferred
                        )
                else:
                    # 创建新关联
                    model_provider = LLMModelProvider(
                        llm_id=model_id,
                        provider_id=model_data.provider_id,
                        weight=model_data.provider_weight or 10,
                        is_preferred=model_data.is_provider_preferred or False,
                    )
                    session.add(model_provider)

            # 刷新以获取更新后的关联数据
            session.flush()
            session.refresh(model)

            # 使用辅助函数构建返回数据
            model_item = build_model_item_data(model)

            return ApiResponse.success(
                data=model_item, message="Model updated successfully"
            )

    except Exception as e:
        logger.error(f"Failed to update model (ID: {model_id}): {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update model: {str(e)}")
