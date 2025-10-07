import time
from typing import Dict, List, Any, Optional
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import openai
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class AliQwenAdapter(BaseAdapter):
    """AliQwen model adapter - using OpenAI library"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        super().__init__(model_config, api_key)
        # Ensure base_url does not end with / to avoid OpenAI library automatically adding path
        base_url = self.base_url.rstrip("/")
        # Initialize OpenAI client with optimized settings
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=360.0,  # 超时时间 6 分钟
            max_retries=2,  # 重试次数
        )

    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """Format messages to OpenAI format"""
        formatted_messages = []
        for msg in messages:
            formatted_msg = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                formatted_msg["name"] = msg.name
            formatted_messages.append(formatted_msg)
        return formatted_messages

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute AliQwen chat completion request - using OpenAI library"""
        start_time = time.time()

        try:
            # Build request parameters
            params = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stream": request.stream,
                "n": request.n,
                "stop": request.stop,
                "logit_bias": request.logit_bias,
                "user": request.user,
            }

            # Handle thinking parameter (AliQwen支持thinking参数)
            if request.thinking:
                params["thinking"] = request.thinking
                logger.info(f"🧠 AliQwen Thinking参数: {request.thinking}")

            # Filter None values
            filtered_params = {k: v for k, v in params.items() if v is not None}

            # Use OpenAI library to send request
            response = await self.client.chat.completions.create(**filtered_params)

            # Calculate response time
            response_time = time.time() - start_time

            # Update metrics
            tokens_used = response.usage.total_tokens if response.usage else 0
            self.update_metrics(response_time, True, tokens_used)

            # Build standard response - convert OpenAI object to dictionary
            chat_response = ChatResponse(
                id=response.id,
                created=response.created,
                model=response.model,
                choices=[choice.model_dump() for choice in response.choices],
                usage=response.usage.model_dump() if response.usage else None,
                system_fingerprint=getattr(response, "system_fingerprint", None),
            )

            return chat_response

        except openai.APIError as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)

            # Update health status based on error status code
            if hasattr(e, "status_code"):
                if e.status_code >= 500:
                    self.health_status = HealthStatus.UNHEALTHY
                elif e.status_code >= 400:
                    self.health_status = HealthStatus.DEGRADED

            raise Exception(f"AliQwen API error: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"AliQwen adapter error: {str(e)}")

    async def stream_chat_completion(self, request: ChatRequest):
        """Execute AliQwen stream chat completion request - using OpenAI library"""
        import asyncio

        start_time = time.time()
        logger.info(f"🔥 AliQwen适配器开始流式请求 - 模型: {self.model_name}")

        try:
            # 计时：参数构建
            param_start = time.time()

            # Build request parameters
            params = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stream": True,  # Force enable streaming
                "n": request.n,
                "stop": request.stop,
                "logit_bias": request.logit_bias,
                "user": request.user,
            }

            # Handle thinking parameter (AliQwen支持thinking参数)
            if request.thinking:
                params["thinking"] = request.thinking
                logger.info(f"🧠 AliQwen流式请求Thinking参数: {request.thinking}")

            # Filter None values
            filtered_params = {k: v for k, v in params.items() if v is not None}

            param_time = time.time() - param_start
            logger.info(f"📤 参数构建完成 ({param_time*1000:.1f}ms) - 发送到AliQwen")

            # 计时：API调用
            api_start = time.time()
            stream = await self.client.chat.completions.create(**filtered_params)
            api_time = time.time() - api_start
            logger.info(f"🚀 API连接建立完成 ({api_time*1000:.1f}ms)")

            # 实时chunk转发机制
            first_chunk_received = False
            chunk_count = 0

            # Directly return the native streaming response
            async for chunk in stream:
                chunk_count += 1

                # 首个chunk性能监控
                if not first_chunk_received:
                    first_chunk_received = True
                    delay = time.time() - start_time
                    logger.info(f"⚡ 首个chunk接收，延迟: {delay:.3f}s")

                # Convert JSON to SSE format
                yield f"data: {chunk.model_dump_json()}\n\n"

            total_time = time.time() - start_time
            logger.info(
                f"✅ AliQwen实时流式响应完成 - 总耗时: {total_time:.3f}秒，处理chunk: {chunk_count}"
            )

            # Update metrics
            response_time = time.time() - start_time
            self.update_metrics(response_time, True)

        except openai.APIError as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)

            # Update health status based on error status code
            if hasattr(e, "status_code"):
                if e.status_code >= 500:
                    self.health_status = HealthStatus.UNHEALTHY
                elif e.status_code >= 400:
                    self.health_status = HealthStatus.DEGRADED

            raise Exception(f"AliQwen stream API error: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"AliQwen stream adapter error: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """Execute AliQwen health check - using OpenAI library"""
        try:
            # Try simple chat request
            try:
                # Send a simple test request
                test_response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )
                logger.info(
                    f"AliQwenAdapter health check successful - test chat completed"
                )
                self.health_status = HealthStatus.HEALTHY
                self.metrics.last_health_check = time.time()
                return HealthStatus.HEALTHY
            except Exception as e:
                logger.info(f"Test chat request failed: {str(e)}")

            # If all fail, mark as degraded
            logger.info(f"AliQwenAdapter health check failed, marked as degraded")
            self.health_status = HealthStatus.DEGRADED
            return HealthStatus.DEGRADED

        except openai.AuthenticationError:
            # Authentication error
            self.health_status = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY
        except openai.APIError as e:
            # API error
            if hasattr(e, "status_code") and e.status_code == 401:
                self.health_status = HealthStatus.UNHEALTHY
            else:
                self.health_status = HealthStatus.DEGRADED
            return self.health_status
        except Exception as e:
            # Other error
            self.health_status = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY

    async def create_embedding(self, text: str) -> Dict[str, Any]:
        """Create text embedding - using OpenAI library"""
        try:
            response = await self.client.embeddings.create(
                model="text-embedding-v1", input=text
            )

            return {
                "data": response.data,
                "model": response.model,
                "usage": response.usage,
            }

        except Exception as e:
            raise Exception(f"AliQwen embedding creation error: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """Get available model list"""
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            return response.json().get("data", [])

        except Exception as e:
            raise Exception(f"AliQwen model list get error: {str(e)}")

    async def create_image(
        self,
        prompt: str,
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image from text prompt (AliQwen does not support image generation)"""
        raise NotImplementedError("AliQwen does not support image generation")

    async def edit_image(
        self,
        image: str,
        prompt: str,
        mask: Optional[str] = None,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Edit image based on prompt and optional mask (AliQwen does not support image editing)"""
        raise NotImplementedError("AliQwen does not support image editing")

    async def create_image_variation(
        self,
        image: str,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image variations from base image (AliQwen does not support image variations)"""
        raise NotImplementedError("AliQwen does not support image variations")
