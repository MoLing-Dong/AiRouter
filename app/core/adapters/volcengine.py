import time
from typing import Dict, List, Any, Optional
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import openai
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class VolcengineAdapter(BaseAdapter):
    """Volcengine model adapter - using OpenAI library"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        super().__init__(model_config, api_key)
        # Ensure base_url does not end with /, avoid OpenAI library automatically adding path
        base_url = self.base_url.rstrip("/")
        # Initialize OpenAI client with optimized settings
        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=10.0,  # 减少超时时间
            max_retries=1,  # 减少重试次数以避免延迟
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
        """Execute Volcengine chat completion request - using OpenAI library"""
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

            # Handle thinking parameter using extra_body (Volcengine specific)
            thinking_param = request.thinking
            if thinking_param and isinstance(thinking_param, dict):
                thinking_type = thinking_param.get("type")
                if thinking_type and thinking_type in ["enabled", "disabled", "auto"]:
                    logger.info(f"🧠 Thinking参数: {thinking_type}")
                    # Add thinking parameter to extra_body for Volcengine API
                    params["extra_body"] = {
                        "thinking": {
                            "type": thinking_type  # "enabled", "disabled", or "auto"
                        }
                    }

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

            raise Exception(f"Volcengine API error: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Volcengine adapter error: {str(e)}")

    async def stream_chat_completion(self, request: ChatRequest):
        """Execute Volcengine stream chat completion request - using OpenAI library"""
        import asyncio

        start_time = time.time()
        logger.info(f"🔥 Volcengine适配器开始流式请求 - 模型: {self.model_name}")

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
                "stream": True,  # 强制启用流式
                "n": request.n,
                "stop": request.stop,
                "logit_bias": request.logit_bias,
                "user": request.user,
            }

            # Handle thinking parameter using extra_body (Volcengine specific)
            thinking_param = request.thinking
            if thinking_param and isinstance(thinking_param, dict):
                thinking_type = thinking_param.get("type")
                if thinking_type and thinking_type in ["enabled", "disabled", "auto"]:
                    logger.info(f"🧠 流式请求Thinking参数: {thinking_type}")
                    # Add thinking parameter to extra_body for Volcengine API
                    params["extra_body"] = {
                        "thinking": {
                            "type": thinking_type  # "enabled", "disabled", or "auto"
                        }
                    }

            # Filter None values
            filtered_params = {k: v for k, v in params.items() if v is not None}

            param_time = time.time() - param_start
            logger.info(f"📤 参数构建完成 ({param_time*1000:.1f}ms) - 发送到Volcengine")
            # 打印params
            logger.debug(f"🔍 参数: {params}")
            # 计时：API调用
            api_start = time.time()
            stream = await self.client.chat.completions.create(**filtered_params)
            api_time = time.time() - api_start
            logger.info(f"🚀 API连接建立完成 ({api_time*1000:.1f}ms)")

            # 实时chunk转发机制
            first_chunk_received = False

            # 使用异步迭代器实现接收到就立即转发
            async for chunk in stream:
                # 首个chunk性能监控
                if not first_chunk_received:
                    first_chunk_received = True
                    delay = time.time() - start_time
                    logger.info(f"⚡ 首个chunk接收，延迟: {delay:.3f}s")

                # 零延迟转换和转发 - 保持SSE格式
                sse_chunk = f"data: {chunk.model_dump_json()}\n\n"
                yield sse_chunk

            total_time = time.time() - start_time
            logger.info(f"✅ Volcengine实时流式响应完成 - 总耗时: {total_time:.3f}秒")

            # Update metrics
            response_time = time.time() - start_time
            self.update_metrics(response_time, True)

        except openai.APIError as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)

            logger.error(f"❌ Volcengine API错误: {str(e)}")

            # Update health status based on error status code
            if hasattr(e, "status_code"):
                if e.status_code >= 500:
                    self.health_status = HealthStatus.UNHEALTHY
                elif e.status_code >= 400:
                    self.health_status = HealthStatus.DEGRADED

            raise Exception(f"Volcengine stream API error: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            logger.error(f"❌ Volcengine适配器错误: {str(e)}")
            raise Exception(f"Volcengine stream adapter error: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """Execute Volcengine health check - using OpenAI library"""
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
                    f"VolcengineAdapter health check successful - test chat completion"
                )
                self.health_status = HealthStatus.HEALTHY
                self.metrics.last_health_check = time.time()
                return HealthStatus.HEALTHY
            except Exception as e:
                logger.info(f"Test chat request failed: {str(e)}")

            # If all fail, mark as degraded
            logger.info(f"VolcengineAdapter health check failed, mark as degraded")
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
            raise Exception(f"Volcengine embedding creation error: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """Get available model list - using OpenAI library"""
        try:
            response = await self.client.models.list()
            return [model.model_dump() for model in response.data]

        except Exception as e:
            raise Exception(f"Volcengine model list get error: {str(e)}")

    async def create_image(
        self,
        prompt: str,
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image from text prompt using Volcengine API"""
        try:
            payload = {
                "prompt": prompt,
                "n": n,
                "size": size,
                "response_format": response_format,
            }

            # Add quality and style for DALL-E 3 compatible models
            if "dall-e-3" in self.model_name.lower():
                payload["quality"] = quality
                payload["style"] = style

            response = await self.client.images.generate(**payload)
            return response.data

        except Exception as e:
            raise Exception(f"Volcengine image generation error: {str(e)}")

    async def edit_image(
        self,
        image: str,
        prompt: str,
        mask: Optional[str] = None,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Edit image based on prompt and optional mask using Volcengine API"""
        try:
            payload = {
                "image": image,
                "prompt": prompt,
                "n": n,
                "size": size,
                "response_format": response_format,
            }

            if mask:
                payload["mask"] = mask

            response = await self.client.images.edit(**payload)
            return response.data

        except Exception as e:
            raise Exception(f"Volcengine image editing error: {str(e)}")

    async def create_image_variation(
        self,
        image: str,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image variations from base image using Volcengine API"""
        try:
            payload = {
                "image": image,
                "n": n,
                "size": size,
                "response_format": response_format,
            }

            response = await self.client.images.create_variation(**payload)
            return response.data

        except Exception as e:
            raise Exception(f"Volcengine image variation creation error: {str(e)}")
