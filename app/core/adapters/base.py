from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
import asyncio
import time
from enum import Enum
import httpx
import json
from app.utils.logging_config import get_factory_logger

# 获取日志器
logger = get_factory_logger()


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Message(BaseModel):
    role: MessageRole
    content: str
    name: Optional[str] = None
    function_call: Optional[Dict] = None


class FunctionCall(BaseModel):
    name: str
    arguments: str


class Tool(BaseModel):
    type: str = "function"
    function: Dict[str, Any]


class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = None
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    tools: Optional[List[Tool]] = None
    tool_choice: Optional[str] = None
    stream: Optional[bool] = False


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict]
    usage: Optional[Dict] = None
    system_fingerprint: Optional[str] = None


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ModelMetrics(BaseModel):
    response_time: float = 0.0
    success_rate: float = 1.0
    cost_per_1k_tokens: float = 0.0
    total_requests: int = 0
    total_tokens: int = 0
    last_health_check: float = 0.0
    error_count: int = 0


class BaseAdapter(ABC):
    """基础适配器接口，所有模型适配器必须继承此类"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        self.model_config = model_config
        self.api_key = api_key
        self.base_url = model_config.get("base_url")
        self.model_name = model_config.get("model")
        self.provider = model_config.get("provider")

        # 初始化指标
        self.metrics = ModelMetrics(
            cost_per_1k_tokens=model_config.get("cost_per_1k_tokens", 0.0),
            last_health_check=time.time(),
        )
        self.health_status = HealthStatus.HEALTHY

        # HTTP客户端
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    @abstractmethod
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """执行聊天完成请求"""
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """执行健康检查"""
        pass

    @abstractmethod
    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """格式化消息为特定提供商的格式"""
        pass

    async def stream_chat_completion(self, request: ChatRequest):
        """流式聊天完成 - 子类必须重写此方法以支持真正的流式响应"""
        raise NotImplementedError("This adapter does not support streaming")

    def update_metrics(self, response_time: float, success: bool, tokens_used: int = 0):
        """更新模型指标"""
        self.metrics.response_time = response_time
        self.metrics.total_requests += 1
        self.metrics.total_tokens += tokens_used

        if success:
            # 更新成功率
            total_requests = self.metrics.total_requests
            current_success_rate = self.metrics.success_rate
            self.metrics.success_rate = (
                current_success_rate * (total_requests - 1) + 1
            ) / total_requests
        else:
            # 失败时降低成功率
            self.metrics.error_count += 1
            total_requests = self.metrics.total_requests
            current_success_rate = self.metrics.success_rate
            self.metrics.success_rate = (
                current_success_rate * (total_requests - 1)
            ) / total_requests

    def get_cost_estimate(self, tokens: int) -> float:
        """估算成本"""
        return (tokens / 1000) * self.metrics.cost_per_1k_tokens

    def get_performance_score(self) -> float:
        """计算性能评分（用于负载均衡）"""
        # 综合考虑响应时间、成功率和成本
        response_time_score = max(
            0, 1 - (self.metrics.response_time / 10)
        )  # 10秒为基准
        cost_score = max(
            0, 1 - (self.metrics.cost_per_1k_tokens / 0.1)
        )  # 0.1美元为基准
        success_score = self.metrics.success_rate

        # 加权平均
        return response_time_score * 0.4 + cost_score * 0.3 + success_score * 0.3

    async def close(self):
        """关闭HTTP客户端"""
        if hasattr(self.client, "aclose"):
            await self.client.aclose()
        elif hasattr(self.client, "close"):
            await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
