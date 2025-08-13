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
        raise HTTPException(status_code=500, detail=f"Get database models failed: {str(e)}")


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
        return {
            "message": "Model created successfully",
            "id": model.id,
            "name": model.name,
        }
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
        raise HTTPException(status_code=500, detail=f"Get providers list failed: {str(e)}")


@db_router.post("/providers")
async def create_db_provider(provider_data: LLMProviderCreate):
    """Create database provider"""
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


@db_router.post("/model-providers")
async def create_db_model_provider(model_provider_data: LLMModelProviderCreate):
    """Create model-provider association"""
    try:
        # Check if model-provider association already exists
        existing_mp = db_service.get_model_provider_by_ids(
            model_provider_data.llm_id, model_provider_data.provider_id
        )

        if existing_mp:
            raise HTTPException(
                status_code=400,
                detail=f"Model-provider association already exists: model ID {model_provider_data.llm_id}, provider ID {model_provider_data.provider_id}",
            )

        model_provider = db_service.create_model_provider(model_provider_data)
        return {"message": "Model-provider association created successfully", "id": model_provider.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Create model-provider association failed: {str(e)}"
        )


# Update model-provider association
@db_router.put("/model-providers/{model_provider_id}")
async def update_db_model_provider(
    model_provider_id: int, model_provider_data: LLMModelProviderUpdate
):
    """Update model-provider association"""
    try:
        model_provider = db_service.update_model_provider(
            model_provider_id, model_provider_data
        )
        return {"message": "Model-provider association updated successfully", "id": model_provider.id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Update model-provider association failed: {str(e)}"
        )

@db_router.post("/model-params")
async def create_db_model_param(param_data: LLMModelParamCreate):
    """Create model parameter"""
    try:
        # Check if model parameter already exists
        existing_param = db_service.get_model_param_by_key(
            param_data.llm_id,
            param_data.provider_id,
            param_data.param_key,
        )

        if existing_param:
            raise HTTPException(
                status_code=400,
                detail=f"Model parameter already exists: model ID {param_data.llm_id}, parameter key {param_data.param_key}",
            )

        param = db_service.create_model_param(param_data)
        return {"message": "Model parameter created successfully", "param_id": param.param_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create model parameter failed: {str(e)}")
