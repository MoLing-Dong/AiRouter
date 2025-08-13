from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json

from app.core.adapters import ChatRequest, Message, MessageRole
from app.services.router import router
from app.utils.logging_config import get_chat_logger

# Get logger
logger = get_chat_logger()


chat_router = APIRouter(prefix="/v1", tags=["Chat"])


class ChatCompletionRequest(BaseModel):
    """OpenAI compatible chat completion request"""

    model: str
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str] = None
    stream: Optional[bool] = False
    n: Optional[int] = 1
    stop: Optional[List[str]] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None


class ChatCompletionResponse(BaseModel):
    """OpenAI compatible chat completion response"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None  # Change to Any to compatible with different usage formats,
    system_fingerprint: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """Stream response data chunk"""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


@chat_router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI compatible chat completion interface"""
    try:
        # Check if model is available
        from app.services import adapter_manager

        available_models = adapter_manager.get_available_models()

        if request.model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"Model '{request.model}' is not available. Available models: {available_models}",
            )

        # Convert message format
        messages = []
        for msg in request.messages:
            message = Message(
                role=MessageRole(msg["role"]),
                content=msg["content"],
                name=msg.get("name"),
                function_call=msg.get("function_call"),
            )
            messages.append(message)

        # Build ChatRequest
        chat_request = ChatRequest(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=request.frequency_penalty,
            presence_penalty=request.presence_penalty,
            tools=request.tools,
            tool_choice=request.tool_choice,
            stream=request.stream,
        )

        if request.stream:
            logger.info(f"Stream response: {chat_request}")
            # Stream response
            return StreamingResponse(
                stream_chat_completion(chat_request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # Disable nginx buffering
                },
            )
        else:
            # Normal response
            response = await router.route_request(chat_request)

            # Convert to OpenAI compatible format
            return ChatCompletionResponse(
                id=response.id,
                created=response.created,
                model=response.model,
                choices=response.choices,
                usage=response.usage,
                system_fingerprint=response.system_fingerprint,
            )

    except Exception as e:
        import traceback

        error_detail = f"Chat completion failed: {str(e)}\n{traceback.format_exc()}"
        logger.error(f"API error detail: {error_detail}")
        raise HTTPException(status_code=500, detail=f"Chat completion failed: {str(e)}")


async def stream_chat_completion(request: ChatRequest):
    """Stream chat completion"""
    try:
        # Get adapter manager
        from app.services import adapter_manager

        # Get best adapter
        adapter = adapter_manager.get_best_adapter(request.model)
        logger.info(f"Get adapter: {adapter}")
        if not adapter:
            logger.error(f"No adapter found for model {request.model}")
            yield f"data: {json.dumps({'error': 'No available adapter for model'})}\n\n"
            return

        # Call adapter to stream response
        try:
            # Check if adapter supports stream response
            if hasattr(adapter, "stream_chat_completion"):
                logger.info(f"Start stream response, adapter type: {type(adapter).__name__}")
                async for chunk in adapter.stream_chat_completion(request):
                    # Return native stream response
                    yield chunk
            else:
                # If adapter does not support stream, return error
                yield f"data: {json.dumps({'error': 'This model does not support streaming'})}\n\n"
                return

        except Exception as e:
            logger.error(f"Stream response failed: {e}")
            yield f"data: {json.dumps({'error': f'Stream response failed: {str(e)}'})}\n\n"
            return

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@chat_router.post("/embeddings")
async def create_embeddings(request: Dict[str, Any]):
    """Create text embedding"""
    try:
        model = request.get("model", "text-embedding-v1")
        input_text = request.get("input")

        if not input_text:
            raise HTTPException(status_code=400, detail="Missing input parameter")

        # Here we need to implement embedding functionality
        # For now, return example response
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1] * 1536,  # Example embedding vector
                    "index": 0,
                }
            ],
            "model": model,
            "usage": {
                "prompt_tokens": len(input_text.split()),
                "total_tokens": len(input_text.split()),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Create embedding failed: {str(e)}")
