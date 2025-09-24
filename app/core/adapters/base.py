from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel
import asyncio
import time
from enum import Enum
import httpx
import json
from app.utils.logging_config import get_factory_logger
from app.models import HealthStatusEnum
from app.services.database.database_service import db_service

# Get logger
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
    """Base adapter interface, all model adapters must inherit this class"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        self.model_config = model_config
        self.api_key = api_key
        self.base_url = model_config.get("base_url")
        self.model_name = model_config.get("model")
        self.provider = model_config.get("provider")
        self.model_id = model_config.get("model_id")  # 添加模型ID
        self.provider_id = model_config.get("provider_id")  # 添加提供商ID
        self.api_key_id = model_config.get("api_key_id")  # 添加API key ID用于用量追踪

        # Initialize metrics
        self.metrics = ModelMetrics(
            cost_per_1k_tokens=model_config.get("cost_per_1k_tokens", 0.0),
            last_health_check=time.time(),
        )
        self.health_status = HealthStatus.HEALTHY

        # HTTP client
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    @abstractmethod
    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute chat completion request"""
        pass

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Execute health check"""
        pass

    @abstractmethod
    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """Format messages to specific provider format"""
        pass

    async def stream_chat_completion(self, request: ChatRequest):
        """Stream chat completion - subclass must override this method to support true streaming response"""
        raise NotImplementedError("This adapter does not support streaming")

    async def create_image(
        self,
        prompt: str,
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image from text prompt - subclass must override this method to support image generation"""
        raise NotImplementedError("This adapter does not support image generation")

    async def edit_image(
        self,
        image: str,
        prompt: str,
        mask: Optional[str] = None,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Edit image based on prompt and optional mask - subclass must override this method to support image editing"""
        raise NotImplementedError("This adapter does not support image editing")

    async def create_image_variation(
        self,
        image: str,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image variations from base image - subclass must override this method to support image variations"""
        raise NotImplementedError("This adapter does not support image variations")

    def update_metrics(self, response_time: float, success: bool, tokens_used: int = 0):
        """Update model metrics"""
        self.metrics.response_time = response_time
        self.metrics.total_requests += 1
        self.metrics.total_tokens += tokens_used

        if success:
            # Update success rate
            total_requests = self.metrics.total_requests
            current_success_rate = self.metrics.success_rate
            self.metrics.success_rate = (
                current_success_rate * (total_requests - 1) + 1
            ) / total_requests
        else:
            # When failed, reduce success rate
            self.metrics.error_count += 1
            total_requests = self.metrics.total_requests
            current_success_rate = self.metrics.success_rate
            self.metrics.success_rate = (
                current_success_rate * (total_requests - 1)
            ) / total_requests

        # Update last health check time
        self.metrics.last_health_check = time.time()

        # Try to sync metrics to database if we have model_id and provider_id
        if (
            hasattr(self, "model_id")
            and hasattr(self, "provider_id")
            and self.model_id
            and self.provider_id
        ):
            try:
                from app.services.monitoring.health_check_service import HealthCheckService
                from app.services.database.database_service import db_service

                health_service = HealthCheckService(db_service)
                health_service.sync_adapter_metrics_to_database(
                    model_id=self.model_id,
                    provider_id=self.provider_id,
                    response_time=response_time,
                    success=success,
                    tokens_used=tokens_used,
                    cost=(
                        self.get_cost_estimate(tokens_used) if tokens_used > 0 else 0.0
                    ),
                )
            except Exception as e:
                # Log error but don't fail the main operation
                import logging

                logging.getLogger(__name__).warning(
                    f"Failed to sync metrics to database: {e}"
                )

    def get_cost_estimate(self, tokens: int) -> float:
        """Estimate cost"""
        return (tokens / 1000) * self.metrics.cost_per_1k_tokens

    def get_performance_score(self) -> float:
        """Calculate performance score (used for load balancing)"""
        # Consider response time, success rate and cost
        response_time_score = max(
            0, 1 - (self.metrics.response_time / 10)
        )  # 10 seconds as baseline
        cost_score = max(
            0, 1 - (self.metrics.cost_per_1k_tokens / 0.1)
        )  # 0.1 dollar as baseline
        success_score = self.metrics.success_rate

        # Weighted average
        return response_time_score * 0.4 + cost_score * 0.3 + success_score * 0.3

    async def close(self):
        """Close HTTP client"""
        if hasattr(self.client, "aclose"):
            await self.client.aclose()
        elif hasattr(self.client, "close"):
            await self.client.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def sync_health_status_to_database(
        self, health_status: str, error_message: str = None
    ):
        """Sync health status to database

        Args:
            health_status: Current health status
            error_message: Error message if any
        """
        if (
            not hasattr(self, "model_id")
            or not hasattr(self, "provider_id")
            or not self.model_id
            or not self.provider_id
        ):
            return False

        try:
            from app.services.monitoring.health_check_service import HealthCheckService
            from app.services.database.database_service import db_service

            health_service = HealthCheckService(db_service)
            return health_service.sync_adapter_health_to_database(
                model_id=self.model_id,
                provider_id=self.provider_id,
                health_status=health_status,
                response_time=self.metrics.response_time,
                success=self.metrics.success_rate > 0.5,  # Rough estimate
                error_message=error_message,
            )
        except Exception as e:
            import logging

            logging.getLogger(__name__).warning(
                f"Failed to sync health status to database: {e}"
            )
            return False

    def _convert_health_status(self, health_status: HealthStatus) -> str:
        """Convert health status enum to database format"""
        if health_status == HealthStatus.HEALTHY:
            return "healthy"
        elif health_status == HealthStatus.DEGRADED:
            return "degraded"
        else:
            return "unhealthy"
