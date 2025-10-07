import asyncio
import time
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

chat_router = APIRouter(tags=["Chat"])


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
    thinking: Optional[Dict[str, Any]] = None


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
        # 请求开始计时和适配器获取合并
        request_start = time.time()
        logger.info(f"📥 收到聊天请求 - 模型: {request.model}")

        # 快速路径：直接获取适配器（合并导入和调用）
        from app.services import adapter_manager

        adapter = adapter_manager.get_best_adapter_fast(
            request.model, skip_version_check=True
        )

        # 如果没有找到适配器，尝试重新加载配置
        if not adapter:
            logger.info(f"⚠️ 未找到模型适配器，尝试重新加载配置: {request.model}")

            # Use lock to prevent multiple simultaneous reloads
            async with _config_reload_lock:
                try:
                    # 重新加载配置
                    adapter_manager.load_models_from_database()

                    # 再次尝试获取适配器
                    adapter = adapter_manager.get_best_adapter_fast(
                        request.model, skip_version_check=True
                    )

                    if not adapter:
                        # 获取可用模型列表用于错误消息
                        available_models = list(adapter_manager.model_configs.keys())
                        raise HTTPException(
                            status_code=400,
                            detail=f"Model '{request.model}' is not available. Available models: {available_models}",
                        )
                except Exception as reload_error:
                    logger.error(f"重新加载配置失败: {reload_error}")
                    available_models = list(adapter_manager.model_configs.keys())
                    raise HTTPException(
                        status_code=400,
                        detail=f"Model '{request.model}' is not available. Available models: {available_models}",
                    )

        # 快速消息格式转换（减少中间变量）
        messages = [
            Message(
                role=MessageRole(msg["role"]),
                content=msg["content"],
                name=msg.get("name"),
                function_call=msg.get("function_call"),
            )
            for msg in request.messages
        ]

        # 快速ChatRequest构建
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
            n=request.n,
            stop=request.stop,
            logit_bias=request.logit_bias,
            user=request.user,
            thinking=request.thinking,
        )

        # 总预处理时间（减少日志I/O）
        total_prep_time = time.time() - request_start
        logger.info(f"⚡ 请求预处理完成，总耗时: {total_prep_time*1000:.1f}ms")

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
            # Normal response - use fast adapter method for better performance
            from app.services import adapter_manager

            adapter = adapter_manager.get_best_adapter_fast(
                chat_request.model, skip_version_check=True
            )

            if not adapter:
                raise HTTPException(
                    status_code=503,
                    detail=f"No available adapter for model {chat_request.model}",
                )

            # Use adapter directly instead of router for better performance
            response = await adapter.chat_completion(chat_request)

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
        # 快速获取适配器（减少中间变量和时间计算）
        from app.services import adapter_manager

        adapter = adapter_manager.get_best_adapter_fast(
            request.model, skip_version_check=True
        )

        if not adapter:
            logger.error(f"❌ 未找到模型适配器: {request.model}")
            error_msg = json.dumps({"error": "No available adapter for model"})
            yield f"data: {error_msg}\n\n"
            return

        # Call adapter to stream response
        try:
            # Check if adapter supports stream response
            if hasattr(adapter, "stream_chat_completion"):
                # 开始流式处理，减少日志以提升性能

                # 计时：流式生成器创建
                generator_start = time.time()

                # 实时chunk转发管道 - 接收到就立即转发
                try:
                    # 获取适配器的流式响应生成器
                    stream_generator = adapter.stream_chat_completion(request)

                    generator_time = time.time() - generator_start
                    logger.info(f"🔄 生成器创建完成 ({generator_time*1000:.1f}ms)")

                    # 性能监控标志
                    first_chunk_received = False

                    # 实时转发循环 - 零延迟转发
                    async for chunk in stream_generator:
                        # 首个chunk性能记录
                        if not first_chunk_received:
                            first_chunk_received = True
                            total_delay = time.time() - start_time
                            logger.info(f"⚡ 首chunk到达，总延迟: {total_delay:.3f}s")

                        # 立即转发chunk
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
