import asyncio
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json

from app.core.adapters import ChatRequest, Message, MessageRole
from app.services.load_balancing.router import router
from app.utils.simple_auth import require_api_key
from app.utils.logging_config import get_chat_logger

# Get logger
logger = get_chat_logger()

# Global lock for configuration reloading
_config_reload_lock = asyncio.Lock()

anthropic_router = APIRouter(tags=["Anthropic"])


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
async def create_message(
    request: AnthropicMessageRequest, api_key: str = Depends(require_api_key)
):
    """Anthropic compatible messages endpoint"""
    try:
        # 请求开始计时
        import time

        request_start = time.time()
        logger.info(f"📥 收到Anthropic消息请求 - 模型: {request.model}")

        # 快速路径：直接获取适配器（避免数据库查询）
        from app.services.adapters import adapter_manager

        adapter = adapter_manager.get_best_adapter_fast(
            request.model, skip_version_check=True
        )

        # 如果没有找到适配器，尝试重新加载配置（仅在必要时）
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

        # 快速消息格式转换（优化版本）
        messages = [
            Message(
                role=MessageRole(msg.role),
                content=" ".join([content.text for content in msg.content]),
                name=None,
                function_call=None,
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
            frequency_penalty=0.0,  # Anthropic doesn't use these
            presence_penalty=0.0,  # Anthropic doesn't use these
            tools=None,  # Anthropic doesn't use tools in this format
            tool_choice=None,
            stream=request.stream,
        )

        # 总预处理时间
        total_prep_time = time.time() - request_start
        logger.info(f"⚡ Anthropic请求预处理完成，总耗时: {total_prep_time*1000:.1f}ms")

        if request.stream:
            logger.info(f"🌊 启动Anthropic流式响应: {chat_request.model}")
            # Stream response - 使用与 Anthropic API 兼容的响应头
            return StreamingResponse(
                stream_anthropic_message(chat_request),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",  # 禁用 nginx 缓冲
                    "X-Content-Type-Options": "nosniff",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "*",
                    "Transfer-Encoding": "chunked",
                    "Content-Encoding": "identity",  # 禁用压缩
                    "Pragma": "no-cache",  # HTTP/1.0 兼容
                },
                background=None,  # 不使用后台任务
            )
        else:
            # Normal response - 使用快速适配器方法获得更好性能
            if not adapter:
                raise HTTPException(
                    status_code=503,
                    detail=f"No available adapter for model {chat_request.model}",
                )

            # 直接使用适配器而不是路由器以获得更好性能
            response = await adapter.chat_completion(chat_request)

            # Convert to Anthropic compatible format
            content_text = response.choices[0]["message"]["content"]
            logger.info(
                f"Content text type: {type(content_text)}, value: {content_text}"
            )

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
    import time

    start_time = time.time()
    logger.info(f"🚀 开始Anthropic流式响应处理 - 模型: {request.model}")

    try:
        # 快速获取适配器（减少中间变量和时间计算）
        from app.services.adapters import adapter_manager

        adapter = adapter_manager.get_best_adapter_fast(
            request.model, skip_version_check=True
        )

        if not adapter:
            logger.error(f"❌ 未找到模型适配器: {request.model}")
            yield f"event: error\ndata: {json.dumps({'type': 'error', 'error': {'type': 'not_found_error', 'message': 'No available adapter for model'}})}\n\n"
            return

        # Call adapter to stream response
        try:
            # Check if adapter supports stream response
            if hasattr(adapter, "stream_chat_completion"):
                # 发送消息开始事件
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
                message_start_event = (
                    f"event: message_start\ndata: {json.dumps(message_start_data)}\n\n"
                )
                logger.info(f"📤 发送 message_start 事件")
                yield message_start_event

                # 性能监控标志
                first_chunk_received = False
                content_block_started = False

                async for chunk in adapter.stream_chat_completion(request):
                    # 首个chunk性能记录
                    if not first_chunk_received:
                        first_chunk_received = True
                        total_delay = time.time() - start_time
                        logger.info(
                            f"⚡ Anthropic首chunk到达，总延迟: {total_delay:.3f}s"
                        )

                    # Convert OpenAI-style chunk to Anthropic-style
                    if chunk.startswith("data: "):
                        data_str = chunk[6:].strip()

                        # 忽略 [DONE] 标记
                        if data_str == "[DONE]":
                            continue

                        try:
                            chunk_data = json.loads(data_str)

                            if "choices" in chunk_data and chunk_data["choices"]:
                                delta = chunk_data["choices"][0].get("delta", {})

                                # 发送 content_block_start（第一次有内容时）
                                if (
                                    not content_block_started
                                    and "content" in delta
                                    and delta["content"]
                                ):
                                    content_block_started = True
                                    content_start = {
                                        "type": "content_block_start",
                                        "index": 0,
                                        "content_block": {"type": "text", "text": ""},
                                    }
                                    logger.debug(f"📤 发送 content_block_start 事件")
                                    yield f"event: content_block_start\ndata: {json.dumps(content_start)}\n\n"

                                # 发送 content_block_delta
                                if "content" in delta and delta["content"]:
                                    content_delta = {
                                        "type": "content_block_delta",
                                        "index": 0,
                                        "delta": {
                                            "type": "text_delta",
                                            "text": delta["content"],
                                        },
                                    }
                                    # 只记录第一个和每隔10个delta（避免日志过多）
                                    if not hasattr(
                                        stream_anthropic_message, "delta_count"
                                    ):
                                        stream_anthropic_message.delta_count = 0
                                    stream_anthropic_message.delta_count += 1
                                    yield f"event: content_block_delta\ndata: {json.dumps(content_delta)}\n\n"

                        except json.JSONDecodeError as e:
                            logger.warning(
                                f"⚠️ JSON解析失败: {data_str[:100]}... 错误: {e}"
                            )
                            continue
                        except Exception as e:
                            logger.error(f"❌ chunk处理错误: {e}")
                            continue

                # Send content_block_stop event
                if content_block_started:
                    content_stop = {"type": "content_block_stop", "index": 0}
                    yield f"event: content_block_stop\ndata: {json.dumps(content_stop)}\n\n"

                # Send message_delta event (可选，用于传递最终状态)
                message_delta = {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": 0},  # 可以在这里传递实际的 token 使用量
                }
                logger.debug(f"📤 发送 message_delta 事件")
                yield f"event: message_delta\ndata: {json.dumps(message_delta)}\n\n"

                # Send message_stop event
                logger.debug(f"📤 发送 message_stop 事件")
                yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"

                # 流式响应完成日志
                total_time = time.time() - start_time
                logger.debug(f"✅ Anthropic流式响应完成 - 总耗时: {total_time:.3f}秒")
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
