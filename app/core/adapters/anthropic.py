import time
import uuid
from typing import Dict, List, Optional, Any
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import httpx
import json


class AnthropicAdapter(BaseAdapter):
    """Anthropic Claude model adapter"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        super().__init__(model_config, api_key)

        # 重新创建具有优化配置的httpx客户端
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=360.0,  # 超时时间 6 分钟
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=5),
            headers={
                "anthropic-version": "2023-06-01",
                "x-api-key": api_key,
                "User-Agent": "AiRouter/1.0",
            },
        )

    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """Format messages to Anthropic format"""
        formatted_messages = []
        for msg in messages:
            formatted_msg = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                formatted_msg["name"] = msg.name
            formatted_messages.append(formatted_msg)
        return formatted_messages

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute Anthropic chat completion request"""
        start_time = time.time()

        try:
            # Build request data
            payload = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": request.stream,
            }

            # Anthropic does not support frequency_penalty and presence_penalty
            # Also does not support tools, need special handling

            # Send request
            response = await self.client.post(
                f"{self.base_url}/v1/messages", json=payload
            )

            response.raise_for_status()
            response_data = response.json()

            # Calculate response time
            response_time = time.time() - start_time

            # Update metrics
            tokens_used = response_data.get("usage", {}).get(
                "input_tokens", 0
            ) + response_data.get("usage", {}).get("output_tokens", 0)
            self.update_metrics(response_time, True, tokens_used)

            # Build standard response format
            choices = []
            for content in response_data.get("content", []):
                if content.get("type") == "text":
                    choices.append(
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": content.get("text", ""),
                            },
                            "finish_reason": "stop",
                        }
                    )

            chat_response = ChatResponse(
                id=response_data.get("id", str(uuid.uuid4())),
                created=int(time.time()),
                model=self.model_name,
                choices=choices,
                usage={
                    "prompt_tokens": response_data.get("usage", {}).get(
                        "input_tokens", 0
                    ),
                    "completion_tokens": response_data.get("usage", {}).get(
                        "output_tokens", 0
                    ),
                    "total_tokens": tokens_used,
                },
            )

            return chat_response

        except httpx.HTTPStatusError as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)

            # Update health status based on error status code
            if e.response.status_code >= 500:
                self.health_status = HealthStatus.UNHEALTHY
            elif e.response.status_code >= 400:
                self.health_status = HealthStatus.DEGRADED

            raise Exception(
                f"Anthropic API error: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Anthropic adapter error: {str(e)}")

    async def stream_chat_completion(self, request: ChatRequest):
        """Execute Anthropic stream chat completion request"""
        import asyncio

        start_time = time.time()
        logger.info(f"🔥 Anthropic适配器开始流式请求 - 模型: {self.model_name}")

        try:
            # 计时：参数构建
            param_start = time.time()

            # Build request data
            payload = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,  # Force enable streaming
            }

            param_time = time.time() - param_start
            logger.info(f"📤 参数构建完成 ({param_time*1000:.1f}ms) - 发送到Anthropic")

            # 计时：API调用
            api_start = time.time()

            # Send streaming request
            async with self.client.stream(
                "POST", f"{self.base_url}/v1/messages", json=payload
            ) as response:
                response.raise_for_status()

                api_time = time.time() - api_start
                logger.info(f"🚀 API连接建立完成 ({api_time*1000:.1f}ms)")

                # 实时chunk转发机制
                first_chunk_received = False
                chunk_count = 0

                # Directly return the native streaming response
                async for line in response.aiter_lines():
                    chunk_count += 1

                    # 首个chunk性能监控
                    if not first_chunk_received:
                        first_chunk_received = True
                        delay = time.time() - start_time
                        logger.info(f"⚡ 首个chunk接收，延迟: {delay:.3f}s")

                    yield line

            total_time = time.time() - start_time
            logger.info(
                f"✅ Anthropic实时流式响应完成 - 总耗时: {total_time:.3f}秒，处理chunk: {chunk_count}"
            )

            # Update metrics
            response_time = time.time() - start_time
            self.update_metrics(response_time, True)

        except httpx.HTTPStatusError as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)

            # Update health status based on error status code
            if e.response.status_code >= 500:
                self.health_status = HealthStatus.UNHEALTHY
            elif e.response.status_code >= 400:
                self.health_status = HealthStatus.DEGRADED

            raise Exception(
                f"Anthropic stream API error: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Anthropic stream adapter error: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """Execute health check"""
        try:
            start_time = time.time()
            response = await self.client.get(f"{self.base_url}/v1/models")
            response_time = time.time() - start_time

            if response.status_code == 200:
                logger.info("AnthropicAdapter health check successful")
                self.health_status = HealthStatus.HEALTHY
                self.metrics.last_health_check = time.time()

                # Sync health status to database
                self.sync_health_status_to_database("healthy")

                return HealthStatus.HEALTHY
            else:
                self.health_status = HealthStatus.DEGRADED

                # 异步更新数据库
                await self.update_database_health_status(
                    HealthStatus.DEGRADED, response_time
                )

                return HealthStatus.DEGRADED

        except httpx.ConnectError:
            self.health_status = HealthStatus.UNHEALTHY

            # 异步更新数据库
            await self.update_database_health_status(HealthStatus.UNHEALTHY)

            return HealthStatus.UNHEALTHY
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.health_status = HealthStatus.UNHEALTHY
            else:
                self.health_status = HealthStatus.DEGRADED

            # 异步更新数据库
            await self.update_database_health_status(self.health_status)

            return self.health_status
        except Exception as e:
            self.health_status = HealthStatus.UNHEALTHY

            # 异步更新数据库
            await self.update_database_health_status(HealthStatus.UNHEALTHY)

            return HealthStatus.UNHEALTHY

    async def create_embedding(self, text: str) -> Dict[str, Any]:
        """Create text embedding (Anthropic does not support)"""
        raise NotImplementedError("Anthropic does not support embedding function")

    async def list_models(self) -> List[Dict[str, Any]]:
        """Get available model list"""
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            return response.json().get("data", [])

        except Exception as e:
            raise Exception(f"Anthropic model list get error: {str(e)}")

    async def create_image(
        self,
        prompt: str,
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image from text prompt (Anthropic does not support image generation)"""
        raise NotImplementedError("Anthropic does not support image generation")

    async def edit_image(
        self,
        image: str,
        prompt: str,
        mask: Optional[str] = None,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Edit image based on prompt and optional mask (Anthropic does not support image editing)"""
        raise NotImplementedError("Anthropic does not support image editing")

    async def create_image_variation(
        self,
        image: str,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image variations from base image (Anthropic does not support image variations)"""
        raise NotImplementedError("Anthropic does not support image variations")
