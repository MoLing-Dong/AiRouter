from fastapi import APIRouter, HTTPException
from app.services.database_service import db_service
from app.utils.logging_config import get_factory_logger
from app.models import (
    LLMModelCreate,
    LLMProviderCreate,
)

# Get logger
logger = get_factory_logger()
db_router = APIRouter(prefix="/v1/db", tags=["Database Management"])


@db_router.get("/models")
async def get_db_models():
    """Get database models list"""
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
        raise HTTPException(
            status_code=500, detail=f"Get database models failed: {str(e)}"
        )


@db_router.get("/capabilities")
async def get_capabilities():
    """Get all capabilities"""
    try:
        from app.models.capability import Capability

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
        return result
    except Exception as e:
        logger.error(f"Get capabilities failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Get capabilities failed: {str(e)}"
        )


@db_router.post("/capabilities")
async def create_capability(capability_name: str, description: str = None):
    """Create a new capability"""
    try:
        from app.models.capability import Capability

        session = db_service.get_session()

        # Check if capability already exists
        existing = (
            session.query(Capability)
            .filter_by(capability_name=capability_name.upper())
            .first()
        )
        if existing:
            session.close()
            raise HTTPException(
                status_code=400, detail=f"Capability already exists: {capability_name}"
            )

        # Create new capability
        capability = Capability(
            capability_name=capability_name.upper(), description=description
        )
        session.add(capability)
        session.commit()

        result = {
            "message": "Capability created successfully",
            "capability_id": capability.capability_id,
            "capability_name": capability.capability_name,
            "description": capability.description,
        }

        session.close()
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create capability failed: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Create capability failed: {str(e)}"
        )


@db_router.post("/models")
async def create_db_model(model_data: LLMModelCreate):
    """Create model"""
    try:
        # Check if model already exists
        existing_model = db_service.get_model_by_name(model_data.name)

        if existing_model:
            raise HTTPException(
                status_code=400, detail=f"Model already exists: {model_data.name}"
            )

        model = db_service.create_model(model_data)

        # Prepare response
        response = {
            "message": "Model created successfully",
            "id": model.id,
            "name": model.name,
        }

        # If provider association was created, add provider info to response
        if model_data.provider_id:
            try:
                provider = db_service.get_provider_by_id(model_data.provider_id)
                if provider:
                    response["provider_info"] = {
                        "provider_id": model_data.provider_id,
                        "provider_name": provider.name,
                        "weight": model_data.provider_weight or 10,
                        "is_preferred": model_data.is_provider_preferred or False,
                    }
            except Exception as e:
                logger.warning(f"Failed to get provider info for response: {e}")

        # If capabilities associations were created, add capabilities info to response
        if model_data.capability_ids:
            try:
                from app.models.capability import Capability

                session = db_service.get_session()
                capabilities = []
                for cap_id in model_data.capability_ids:
                    capability = (
                        session.query(Capability)
                        .filter_by(capability_id=cap_id)
                        .first()
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
            except Exception as e:
                logger.warning(f"Failed to get capabilities info for response: {e}")

        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create model failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Create model failed: {str(e)}")


@db_router.get("/providers")
async def get_db_providers():
    """Get database providers list"""
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
        raise HTTPException(
            status_code=500, detail=f"Get providers list failed: {str(e)}"
        )


@db_router.post("/providers")
async def create_db_provider(provider_data: LLMProviderCreate):
    """Create provider"""
    try:
        # Check if provider already exists
        existing_provider = db_service.get_provider_by_name_and_type(
            provider_data.name, provider_data.provider_type
        )

        if existing_provider:
            raise HTTPException(
                status_code=400,
                detail=f"Provider already exists: {provider_data.name} ({provider_data.provider_type})",
            )

        provider = db_service.create_provider(provider_data)
        return {
            "message": "Provider created successfully",
            "provider_id": provider.id,
            "provider_name": provider.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create provider failed: {str(e)}")
