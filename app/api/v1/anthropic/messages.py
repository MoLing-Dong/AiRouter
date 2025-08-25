import asyncio
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

# Global lock for configuration reloading
_config_reload_lock = asyncio.Lock()

anthropic_router = APIRouter(prefix="/v1", tags=["Anthropic"])


class MessageContent(BaseModel):
    """Anthropic message content"""

    type: str = "text"
    text: str


class AnthropicMessage(BaseModel):
    """Anthropic message format"""

    role: str  # "user" or "assistant"
    content: List[MessageContent]


class AnthropicMessageRequest(BaseModel):
    """Anthropic messages API request"""

    model: str
    messages: List[AnthropicMessage]
    max_tokens: Optional[int] = 4096
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    stream: Optional[bool] = False


class AnthropicMessageResponse(BaseModel):
    """Anthropic messages API response"""

    id: str
    type: str = "message"
    role: str = "assistant"
    content: List[Dict[str, Any]]
    model: str
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None


class AnthropicMessageStreamChunk(BaseModel):
    """Anthropic streaming response chunk"""

    type: str
    message: Optional[Dict[str, Any]] = None


@anthropic_router.post("/messages")
async def create_message(request: AnthropicMessageRequest):
    """Anthropic compatible messages endpoint"""
    try:
        # Check if model is available
        from app.services import adapter_manager

        # Only get models that support chat functionality
        available_models = adapter_manager.get_available_models(
            capabilities=["TEXT", "MULTIMODAL_IMAGE_UNDERSTANDING"]
        )

        # If model is not available, try to reload configuration from database
        if request.model not in available_models:
            logger.warning(
                f"Model '{request.model}' not found in available models: {available_models}"
            )
            logger.info("Attempting to reload model configurations from database...")

            # Use lock to prevent multiple simultaneous reloads
            async with _config_reload_lock:
                try:
                    # Check again while holding the lock
                    available_models = adapter_manager.get_available_models(
                        capabilities=["TEXT", "MULTIMODAL_IMAGE_UNDERSTANDING"]
                    )

                    if request.model not in available_models:
                        # Reload configurations from database
                        adapter_manager.load_models_from_database()

                        # Check again after reload
                        available_models = adapter_manager.get_available_models(
                            capabilities=["TEXT", "MULTIMODAL_IMAGE_UNDERSTANDING"]
                        )
                        logger.info(
                            f"After reload, available models: {available_models}"
                        )

                        if request.model not in available_models:
                            raise HTTPException(
                                status_code=400,
                                detail=f"Model '{request.model}' is not available. Available models: {available_models}",
                            )
                except Exception as reload_error:
                    logger.error(
                        f"Failed to reload model configurations: {reload_error}"
                    )
                    raise HTTPException(
                        status_code=400,
                        detail=f"Model '{request.model}' is not available. Available models: {available_models}",
                    )

        # Convert Anthropic message format to internal format
        messages = []
        for msg in request.messages:
            # Combine all content pieces into single text content
            content_text = " ".join([content.text for content in msg.content])

            message = Message(
                role=MessageRole(msg.role),
                content=content_text,
                name=None,
                function_call=None,
            )
            messages.append(message)

        # Build ChatRequest
        chat_request = ChatRequest(
            model=request.model,
            messages=messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            top_p=request.top_p,
            frequency_penalty=0.0,  # Anthropic doesn't use these
            presence_penalty=0.0,  # Anthropic doesn't use these
            tools=None,  # Anthropic doesn't use tools in this format
            tool_choice=None,
            stream=request.stream,
        )

        if request.stream:
            logger.info(f"Stream response: {chat_request}")
            # Stream response
            return StreamingResponse(
                stream_anthropic_message(chat_request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            # Normal response
            response = await router.route_request(chat_request)

            # Convert to Anthropic compatible format
            content_text = response.choices[0]["message"]["content"]
            logger.info(f"Content text type: {type(content_text)}, value: {content_text}")
            
            # Ensure content is always a list format for Anthropic
            if isinstance(content_text, str):
                content_list = [{"type": "text", "text": content_text}]
            elif isinstance(content_text, list):
                content_list = content_text
            else:
                content_list = [{"type": "text", "text": str(content_text)}]
            
            logger.info(f"Content list: {content_list}")
            
            return AnthropicMessageResponse(
                id=response.id,
                model=response.model,
                content=content_list,
                stop_reason=response.choices[0].get("finish_reason"),
                usage=response.usage,
            )

    except Exception as e:
        import traceback

        error_detail = (
            f"Anthropic message creation failed: {str(e)}\n{traceback.format_exc()}"
        )
        logger.error(f"API error detail: {error_detail}")
        raise HTTPException(
            status_code=500, detail=f"Anthropic message creation failed: {str(e)}"
        )


async def stream_anthropic_message(request: ChatRequest):
    """Stream Anthropic message response"""
    try:
        # Get adapter manager
        from app.services import adapter_manager

        # Get best adapter
        adapter = adapter_manager.get_best_adapter(request.model)
        logger.info(f"Get adapter: {adapter}")
        if not adapter:
            logger.error(f"No adapter found for model {request.model}")
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'not_found_error', 'message': 'No available adapter for model'}})}\n\n"
            return

        # Call adapter to stream response
        try:
            # Check if adapter supports stream response
            if hasattr(adapter, "stream_chat_completion"):
                logger.info(
                    f"Start stream response, adapter type: {type(adapter).__name__}"
                )

                # Send message_start event
                import time
                message_start_data = {
                    "type": "message_start",
                    "message": {
                        "id": "msg_" + str(int(time.time() * 1000000) % 1000000),
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": request.model,
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 0, "output_tokens": 0},
                    },
                }
                yield f"event: message_start\ndata: {json.dumps(message_start_data)}\n\n"

                async for chunk in adapter.stream_chat_completion(request):
                    # Convert OpenAI-style chunk to Anthropic-style
                    if chunk.startswith("data: "):
                        chunk_data = json.loads(chunk[6:])
                        if "choices" in chunk_data and chunk_data["choices"]:
                            delta = chunk_data["choices"][0].get("delta", {})
                            if "content" in delta:
                                # Send content block delta
                                content_delta = {
                                    "type": "content_block_delta",
                                    "index": 0,
                                    "delta": {
                                        "type": "text_delta",
                                        "text": delta["content"],
                                    },
                                }
                                yield f"event: content_block_delta\ndata: {json.dumps(content_delta)}\n\n"

                # Send message_stop event
                yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"
            else:
                # If adapter does not support stream, return error
                error_data = {
                    "type": "error",
                    "error": {
                        "type": "streaming_not_supported",
                        "message": "This model does not support streaming",
                    },
                }
                yield f"event: error\ndata: {json.dumps(error_data)}\n\n"
                return

        except Exception as e:
            logger.error(f"Stream response failed: {e}")
            streaming_error_data = {
                "type": "error",
                "error": {
                    "type": "streaming_error",
                    "message": f"Stream response failed: {str(e)}",
                },
            }
            yield f"event: error\ndata: {json.dumps(streaming_error_data)}\n\n"
            return

    except Exception as e:
        internal_error_data = {
            "type": "error",
            "error": {"type": "internal_error", "message": str(e)},
        }
        yield f"event: error\ndata: {json.dumps(internal_error_data)}\n\n"
