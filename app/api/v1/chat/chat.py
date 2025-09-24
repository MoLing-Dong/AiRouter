import asyncio
from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json

from app.core.adapters import ChatRequest, Message, MessageRole
from app.services.load_balancing.router import SmartRouter
from app.utils.simple_auth import require_api_key

# Initialize router
router = SmartRouter()
from app.utils.logging_config import get_chat_logger

# Get logger
logger = get_chat_logger()

# Global lock for configuration reloading
_config_reload_lock = asyncio.Lock()

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
    usage: Optional[Dict[str, Any]] = (
        None  # Change to Any to compatible with different usage formats,
    )
    system_fingerprint: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """Stream response data chunk"""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


@chat_router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest, api_key: str = Depends(require_api_key)
):
    """OpenAI compatible chat completion interface"""
    try:
        # Check if model is available
        from app.services import adapter_manager

        # Only get models that support chat functionality (text processing and multimodal understanding)
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
                    # Check again while holding the lock (in case another request already reloaded)
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
            logger.info(f"🌊 启动实时流式响应管道: {chat_request.model}")
            # 实时流式响应，零缓冲配置
            return StreamingResponse(
                stream_chat_completion(chat_request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # 禁用nginx缓冲
                    "X-Content-Type-Options": "nosniff",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Transfer-Encoding": "chunked",
                    "Content-Encoding": "identity",  # 禁用压缩
                    "Pragma": "no-cache",  # HTTP/1.0兼容
                },
                background=None,  # 不使用后台任务
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
    """Stream chat completion with real-time forwarding"""
    import asyncio
    import time

    start_time = time.time()
    logger.info(f"🚀 开始流式响应处理 - 模型: {request.model}")

    try:
        # Get adapter manager
        from app.services import adapter_manager

        # Get best adapter
        adapter = adapter_manager.get_best_adapter(request.model)
        logger.info(f"📡 获取到适配器: {type(adapter).__name__ if adapter else 'None'}")

        if not adapter:
            logger.error(f"❌ 未找到模型适配器: {request.model}")
            error_msg = json.dumps({"error": "No available adapter for model"})
            yield f"data: {error_msg}\n\n"
            return

        # Call adapter to stream response
        try:
            # Check if adapter supports stream response
            if hasattr(adapter, "stream_chat_completion"):
                logger.info(f"✅ 适配器支持流式响应，开始处理...")

                # 发送开始信号给客户端
                start_signal = json.dumps(
                    {
                        "type": "stream_start",
                        "model": request.model,
                        "timestamp": int(time.time()),
                    }
                )
                yield f"data: {start_signal}\n\n"

                logger.info(f"🔄 建立实时chunk转发管道...")

                # 实时chunk转发管道 - 接收到就立即转发
                try:
                    # 获取适配器的流式响应生成器
                    stream_generator = adapter.stream_chat_completion(request)

                    # 性能监控标志
                    first_chunk_received = False

                    # 实时转发循环 - 保持格式但零延迟转发
                    async for chunk in stream_generator:
                        # 首个chunk性能记录
                        if not first_chunk_received:
                            first_chunk_received = True
                            delay = time.time() - start_time
                            logger.info(f"⚡ 实时转发管道激活，延迟: {delay:.3f}s")

                        # 立即转发chunk（已经是正确的SSE格式）
                        yield chunk

                except asyncio.CancelledError:
                    logger.info("🛑 流式传输被客户端取消")
                    raise
                except Exception as stream_error:
                    logger.error(f"❌ 流式管道错误: {stream_error}")
                    error_msg = json.dumps(
                        {"error": f"Stream pipeline error: {str(stream_error)}"}
                    )
                    yield f"data: {error_msg}\n\n"
                    return

                total_time = time.time() - start_time
                logger.info(f"✅ 实时chunk转发完成 - 总耗时: {total_time:.3f}秒")

                # 发送结束标记
                yield "data: [DONE]\n\n"

            else:
                logger.error(f"❌ 适配器不支持流式响应: {type(adapter).__name__}")
                error_msg = json.dumps(
                    {"error": "This model does not support streaming"}
                )
                yield f"data: {error_msg}\n\n"
                return

        except Exception as e:
            logger.error(f"❌ 流式响应处理失败: {str(e)}")
            error_msg = json.dumps({"error": f"Stream response failed: {str(e)}"})
            yield f"data: {error_msg}\n\n"
            return

    except Exception as e:
        logger.error(f"❌ 流式响应初始化失败: {str(e)}")
        error_msg = json.dumps({"error": f"Stream initialization failed: {str(e)}"})
        yield f"data: {error_msg}\n\n"


@chat_router.post("/embeddings")
async def create_embeddings(
    request: Dict[str, Any], api_key: str = Depends(require_api_key)
):
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
        raise HTTPException(
            status_code=500, detail=f"Create embedding failed: {str(e)}"
        )
