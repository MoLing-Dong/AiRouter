from fastapi import APIRouter, Path
from app.services.database.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import (
    LLMModelCreate,
    LLMProviderCreate,
)

# Get logger
logger = get_factory_logger()
db_router = APIRouter(tags=["Database Management"])


@db_router.get("/models")
async def get_db_models():
    """Get database models list"""
    try:
        models = db_service.get_all_models()
        return {
            "success": True,
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
            ],
        }
    except Exception as e:
        logger.error(f"Get database models failed: {str(e)}")
        return {"success": False, "message": f"Get database models failed: {str(e)}"}


@db_router.delete("/models/{model_id}")
async def delete_db_model(
    model_id: int = Path(..., gt=0, description="模型ID", example=1, title="Model ID")
):
    """
    删除指定的模型

    - **model_id**: 要删除的模型ID（必须大于0）
    """
    try:
        # 检查模型是否存在
        model = db_service.get_model_by_id(model_id)
        if not model:
            return {
                "success": False,
                "message": f"模型不存在：ID {model_id}",
            }
        # 执行删除
        result = db_service.delete_model(model_id)

        if result:
            return {
                "success": True,
                "message": f"模型 '{model.name}' 已成功删除",
                "model_id": model_id,
                "model_name": model.name,
            }
        else:
            return {
                "success": False,
                "message": "删除模型失败",
            }

    except Exception as e:
        logger.error(f"删除模型失败 (ID: {model_id}): {str(e)}")
        return {
            "success": False,
            "message": f"删除模型时发生错误：{str(e)}",
        }


@db_router.get("/capabilities")
async def get_capabilities():
    """Get all capabilities"""
    try:
        from app.models import Capability

        session = db_service.get_session()
        capabilities = session.query(Capability).all()

        result = []
        for cap in capabilities:
            result.append(
                {
                    "capability_id": cap.capability_id,
                    "capability_name": cap.capability_name,
                    "description": cap.description,
                }
            )

        session.close()
        return {"success": True, "capabilities": result}
    except Exception as e:
        logger.error(f"Get capabilities failed: {str(e)}")
        return {"success": False, "message": f"Get capabilities failed: {str(e)}"}


@db_router.post("/capabilities")
async def create_capability(capability_name: str, description: str = None):
    """Create a new capability"""
    try:
        from app.models import Capability

        session = db_service.get_session()

        # Check if capability already exists
        existing = (
            session.query(Capability)
            .filter_by(capability_name=capability_name.upper())
            .first()
        )
        if existing:
            session.close()
            return {
                "success": False,
                "message": f"Capability already exists: {capability_name}",
            }

        # Create new capability
        capability = Capability(
            capability_name=capability_name.upper(), description=description
        )
        session.add(capability)
        session.commit()

        result = {
            "success": True,
            "message": "Capability created successfully",
            "capability_id": capability.capability_id,
            "capability_name": capability.capability_name,
            "description": capability.description,
        }

        session.close()
        return result
    except Exception as e:
        logger.error(f"Create capability failed: {str(e)}")
        return {"success": False, "message": f"Create capability failed: {str(e)}"}


@db_router.post("/models")
async def create_db_model(model_data: LLMModelCreate):
    """Create model - 使用全局异常处理器，代码更简洁"""
    # Check if model already exists
    existing_model = db_service.get_model_by_name(model_data.name)

    if existing_model:
        # 直接抛出异常，全局异常处理器会捕获并返回统一格式
        raise ValueError(f"Model already exists: {model_data.name}")

    model = db_service.create_model(model_data)

    # Prepare response
    response = {
        "success": True,
        "message": "Model created successfully",
        "id": model.id,
        "name": model.name,
    }

    # If provider association was created, add provider info to response
    if model_data.provider_id:
        provider = db_service.get_provider_by_id(model_data.provider_id)
        if provider:
            response["provider_info"] = {
                "provider_id": model_data.provider_id,
                "provider_name": provider.name,
                "weight": model_data.provider_weight or 10,
                "is_preferred": model_data.is_provider_preferred or False,
            }

    # If capabilities associations were created, add capabilities info to response
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
            response["capabilities"] = capabilities

    return response


@db_router.get("/providers")
async def get_db_providers():
    """Get database providers list"""
    try:
        providers = db_service.get_all_providers()
        return {
            "success": True,
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
            ],
        }
    except Exception as e:
        logger.error(f"Get providers list failed: {str(e)}")
        return {"success": False, "message": f"Get providers list failed: {str(e)}"}


@db_router.post("/providers")
async def create_db_provider(provider_data: LLMProviderCreate):
    """Create provider"""
    try:
        # Check if provider already exists
        existing_provider = db_service.get_provider_by_name_and_type(
            provider_data.name, provider_data.provider_type
        )

        if existing_provider:
            return {
                "success": False,
                "message": f"Provider already exists: {provider_data.name} ({provider_data.provider_type})",
            }

        provider = db_service.create_provider(provider_data)
        return {
            "success": True,
            "message": "Provider created successfully",
            "provider_id": provider.id,
            "provider_name": provider.name,
        }
    except Exception as e:
        logger.error(f"Create provider failed: {str(e)}")
        return {"success": False, "message": f"Create provider failed: {str(e)}"}
