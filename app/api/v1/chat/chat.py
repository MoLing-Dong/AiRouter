from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import json
import time
import uuid
import asyncio

from app.core.adapters import ChatRequest, ChatResponse, Message, MessageRole
from app.services.router import router

chat_router = APIRouter(prefix="/v1", tags=["聊天"])


class ChatCompletionRequest(BaseModel):
    """OpenAI兼容的聊天完成请求"""

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
    """OpenAI兼容的聊天完成响应"""

    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Optional[Dict[str, Any]] = None  # 改为Any以兼容不同的usage格式
    system_fingerprint: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    """流式响应的数据块"""

    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


@chat_router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """OpenAI兼容的聊天完成接口"""
    try:
        # 检查模型是否可用
        from app.services import adapter_manager

        available_models = adapter_manager.get_available_models()

        if request.model not in available_models:
            raise HTTPException(
                status_code=400,
                detail=f"模型 '{request.model}' 不可用。可用模型: {available_models}",
            )

        # 转换消息格式
        messages = []
        for msg in request.messages:
            message = Message(
                role=MessageRole(msg["role"]),
                content=msg["content"],
                name=msg.get("name"),
                function_call=msg.get("function_call"),
            )
            messages.append(message)

        # 构建ChatRequest
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
            # 流式响应
            return StreamingResponse(
                stream_chat_completion(chat_request),
                media_type="text/plain",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "Content-Type": "text/event-stream",
                },
            )
        else:
            # 普通响应
            response = await router.route_request(chat_request)

            # 转换为OpenAI兼容格式
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

        error_detail = f"聊天完成失败: {str(e)}\n{traceback.format_exc()}"
        print(f"API错误详情: {error_detail}")
        raise HTTPException(status_code=500, detail=f"聊天完成失败: {str(e)}")


async def stream_chat_completion(request: ChatRequest):
    """流式聊天完成"""
    try:
        # 获取适配器
        adapter = router.get_best_adapter(request.model)
        if not adapter:
            yield f"data: {json.dumps({'error': 'No available adapter for model'})}\n\n"
            return

        # 创建流式响应
        response_id = str(uuid.uuid4())
        created_time = int(time.time())

        # 发送开始标记
        yield f"data: {json.dumps({'id': response_id, 'object': 'chat.completion.chunk', 'created': created_time, 'model': request.model, 'choices': [{'index': 0, 'delta': {'role': 'assistant'}, 'finish_reason': None}]})}\n\n"

        # 这里需要实现流式响应逻辑
        # 由于当前适配器不支持流式，我们先返回一个简单的响应
        content = "这是一个流式响应的示例。"
        for i, char in enumerate(content):
            chunk = {
                "id": response_id,
                "object": "chat.completion.chunk",
                "created": created_time,
                "model": request.model,
                "choices": [
                    {"index": 0, "delta": {"content": char}, "finish_reason": None}
                ],
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            await asyncio.sleep(0.01)  # 模拟流式延迟

        # 发送结束标记
        final_chunk = {
            "id": response_id,
            "object": "chat.completion.chunk",
            "created": created_time,
            "model": request.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@chat_router.post("/embeddings")
async def create_embeddings(request: Dict[str, Any]):
    """创建文本嵌入"""
    try:
        model = request.get("model", "text-embedding-v1")
        input_text = request.get("input")

        if not input_text:
            raise HTTPException(status_code=400, detail="缺少input参数")

        # 这里需要实现嵌入功能
        # 暂时返回示例响应
        return {
            "object": "list",
            "data": [
                {
                    "object": "embedding",
                    "embedding": [0.1] * 1536,  # 示例嵌入向量
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
        raise HTTPException(status_code=500, detail=f"创建嵌入失败: {str(e)}")
