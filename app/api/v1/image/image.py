from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json
import time
import uuid

from app.core.adapters.base import BaseAdapter
from app.services.router import router
from app.utils.logging_config import get_chat_logger

# Get logger
logger = get_chat_logger()


image_router = APIRouter(prefix="/v1", tags=["Images"])


class ImageGenerationRequest(BaseModel):
    """OpenAI compatible image generation request"""

    prompt: str
    model: Optional[str] = "dall-e-3"
    n: Optional[int] = 1
    size: Optional[str] = "1024x1024"
    quality: Optional[str] = "standard"
    style: Optional[str] = "vivid"
    response_format: Optional[str] = "url"
    user: Optional[str] = None


class ImageEditRequest(BaseModel):
    """OpenAI compatible image edit request"""

    image: str  # Base64 encoded image or URL
    prompt: str
    mask: Optional[str] = None  # Base64 encoded mask image
    n: Optional[int] = 1
    size: Optional[str] = "1024x1024"
    response_format: Optional[str] = "url"
    user: Optional[str] = None


class ImageVariationRequest(BaseModel):
    """OpenAI compatible image variation request"""

    image: str  # Base64 encoded image or URL
    n: Optional[int] = 1
    size: Optional[str] = "1024x1024"
    response_format: Optional[str] = "url"
    user: Optional[str] = None


class ImageResponse(BaseModel):
    """OpenAI compatible image response"""

    created: int
    data: List[Dict[str, Any]]


@image_router.post("/images/generations")
async def create_image(request: ImageGenerationRequest):
    """Create image from text prompt"""
    try:
        # Check if model is available
        from app.services import adapter_manager

        # Only get models that support image generation (text-to-image capability)
        available_models = adapter_manager.get_available_models(
            capabilities=["TEXT_TO_IMAGE"]
        )

        if request.model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model}' is not available. Available models: {available_models}",
            )

        # Get best adapter for image generation
        adapter = adapter_manager.get_best_adapter(request.model)
        if not adapter:
            raise HTTPException(
                status_code=400,
                detail=f"No available adapter for model {request.model}",
            )

        # Check if adapter supports image generation
        if not hasattr(adapter, "create_image"):
            raise HTTPException(
                status_code=400,
                detail=f"Model {request.model} does not support image generation",
            )

        # Create image using adapter
        image_data = await adapter.create_image(
            prompt=request.prompt,
            n=request.n,
            size=request.size,
            quality=request.quality,
            style=request.style,
            response_format=request.response_format,
        )

        return ImageResponse(
            created=int(time.time()),
            data=image_data,
        )

    except Exception as e:
        import traceback

        error_detail = f"Image generation failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"API error detail: {error_detail}")
        raise HTTPException(
            status_code=500, detail=f"Image generation failed: {str(e)}"
        )


@image_router.post("/images/edits")
async def edit_image(request: ImageEditRequest):
    """Edit image based on prompt and optional mask"""
    try:
        # Check if model is available
        from app.services import adapter_manager

        # Only get models that support image editing (image-to-image capability)
        available_models = adapter_manager.get_available_models(
            capabilities=["IMAGE_TO_IMAGE"]
        )

        # For image editing, we'll use a default model if none specified
        model = request.model or "dall-e-2"

        if model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not available. Available models: {available_models}",
            )

        # Get best adapter for image editing
        adapter = adapter_manager.get_best_adapter(model)
        if not adapter:
            raise HTTPException(
                status_code=400,
                detail=f"No available adapter for model {model}",
            )

        # Check if adapter supports image editing
        if not hasattr(adapter, "edit_image"):
            raise HTTPException(
                status_code=400,
                detail=f"Model {model} does not support image editing",
            )

        # Edit image using adapter
        image_data = await adapter.edit_image(
            image=request.image,
            prompt=request.prompt,
            mask=request.mask,
            n=request.n,
            size=request.size,
            response_format=request.response_format,
        )

        return ImageResponse(
            created=int(time.time()),
            data=image_data,
        )

    except Exception as e:
        import traceback

        error_detail = f"Image editing failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"API error detail: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Image editing failed: {str(e)}")


@image_router.post("/images/variations")
async def create_image_variation(request: ImageVariationRequest):
    """Create image variations from base image"""
    try:
        # Check if model is available
        from app.services import adapter_manager

        available_models = adapter_manager.get_available_models()

        # For image variations, we'll use a default model if none specified
        model = request.model or "dall-e-2"

        if model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{model}' is not available. Available models: {available_models}",
            )

        # Get best adapter for image variations
        adapter = adapter_manager.get_best_adapter(model)
        if not adapter:
            raise HTTPException(
                status_code=400,
                detail=f"No available adapter for model {model}",
            )

        # Check if adapter supports image variations
        if not hasattr(adapter, "create_image_variation"):
            raise HTTPException(
                status_code=400,
                detail=f"Model {model} does not support image variations",
            )

        # Create image variation using adapter
        image_data = await adapter.create_image_variation(
            image=request.image,
            n=request.n,
            size=request.size,
            response_format=request.response_format,
        )

        return ImageResponse(
            created=int(time.time()),
            data=image_data,
        )

    except Exception as e:
        import traceback

        error_detail = (
            f"Image variation creation failed: {str(e)}\n{traceback.format_exc()}"
        )
        logger.error(f"API error detail: {error_detail}")
        raise HTTPException(
            status_code=500, detail=f"Image variation creation failed: {str(e)}"
        )


@image_router.get("/images/models")
async def list_image_models():
    """List available image generation models"""
    try:
        from app.services import adapter_manager

        available_models = adapter_manager.get_available_models()

        # Filter models that support image generation
        image_models = []
        for model_name in available_models:
            adapter = adapter_manager.get_best_adapter(model_name)
            if adapter and hasattr(adapter, "create_image"):
                image_models.append(
                    {
                        "id": model_name,
                        "object": "model",
                        "created": int(time.time()),
                        "owned_by": "organization",
                        "permission": [],
                        "root": model_name,
                        "parent": None,
                        "capabilities": {
                            "image_generation": True,
                            "image_editing": hasattr(adapter, "edit_image"),
                            "image_variations": hasattr(
                                adapter, "create_image_variation"
                            ),
                        },
                    }
                )

        return {"object": "list", "data": image_models}

    except Exception as e:
        import traceback

        error_detail = (
            f"Failed to list image models: {str(e)}\n{traceback.format_exc()}"
        )
        logger.error(f"API error detail: {error_detail}")
        raise HTTPException(
            status_code=500, detail=f"Failed to list image models: {str(e)}"
        )
