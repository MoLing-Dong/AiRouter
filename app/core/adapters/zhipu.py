import time
import json
from typing import Dict, List, Any, Optional
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import openai
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class ZhipuAdapter(BaseAdapter):
    """Zhipu model adapter - using OpenAI library"""

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

    def _convert_to_openai_format(self, zhipu_chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Zhipu chunk format to OpenAI standard format"""
        openai_chunk = {
            "id": zhipu_chunk.get("id"),
            "object": "chat.completion.chunk",
            "created": zhipu_chunk.get("created"),
            "model": zhipu_chunk.get("model"),
            "choices": [],
        }

        if zhipu_chunk.get("choices"):
            for choice in zhipu_chunk["choices"]:
                delta = choice.get("delta", {})
                openai_delta = {}

                # 处理常规内容
                if delta.get("content"):
                    openai_delta["content"] = delta["content"]

                # 处理智谱特有的推理内容 - 保持为思考内容
                elif delta.get("reasoning_content"):
                    # 保持推理内容作为独立的思考字段
                    openai_delta["reasoning_content"] = delta["reasoning_content"]
                    # 或者使用更通用的思考字段名
                    openai_delta["thinking"] = delta["reasoning_content"]

                # 处理角色
                if delta.get("role"):
                    openai_delta["role"] = delta["role"]

                # 处理工具调用
                if delta.get("tool_calls"):
                    openai_delta["tool_calls"] = delta["tool_calls"]
                if delta.get("function_call"):
                    openai_delta["function_call"] = delta["function_call"]

                openai_choice = {
                    "index": choice.get("index", 0),
                    "delta": openai_delta,
                    "finish_reason": choice.get("finish_reason"),
                    "logprobs": choice.get("logprobs"),
                }

                openai_chunk["choices"].append(openai_choice)

        return openai_chunk

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute Zhipu chat completion request - using OpenAI library"""
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

            raise Exception(f"Zhipu API error: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Zhipu adapter error: {str(e)}")

    async def stream_chat_completion(self, request: ChatRequest):
        """Execute Zhipu stream chat completion request - using OpenAI library"""
        import asyncio

        start_time = time.time()
        logger.info(f"🔥 Zhipu适配器开始流式请求 - 模型: {self.model_name}")

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
            }

            # Filter None values
            filtered_params = {k: v for k, v in params.items() if v is not None}

            param_time = time.time() - param_start
            logger.info(f"📤 参数构建完成 ({param_time*1000:.1f}ms) - 发送到Zhipu")

            # 计时：API调用
            api_start = time.time()
            stream = await self.client.chat.completions.create(**filtered_params)
            api_time = time.time() - api_start
            logger.info(f"🚀 API连接建立完成 ({api_time*1000:.1f}ms)")

            # 实时chunk转发机制
            first_chunk_received = False
            chunk_count = 0

            # 使用异步迭代器实现接收到就立即转发
            async for chunk in stream:
                chunk_count += 1

                # 首个chunk性能监控
                if not first_chunk_received:
                    first_chunk_received = True
                    delay = time.time() - start_time
                    logger.info(f"⚡ 首个chunk接收，延迟: {delay:.3f}s")

                # 过滤空chunk - 检查是否有实际内容
                chunk_dict = chunk.model_dump()
                has_content = False

                if chunk_dict.get("choices"):
                    for choice in chunk_dict["choices"]:
                        delta = choice.get("delta", {})

                        # 检查常规内容
                        if delta.get("content") and delta["content"].strip():
                            has_content = True
                            break

                        # 检查推理内容 (Zhipu特有)
                        if (
                            delta.get("reasoning_content")
                            and delta["reasoning_content"].strip()
                        ):
                            has_content = True
                            break

                        # 检查角色变化或结束标志
                        if delta.get("role") or choice.get("finish_reason"):
                            has_content = True
                            break

                        # 检查工具调用
                        if delta.get("tool_calls") or delta.get("function_call"):
                            has_content = True
                            break

                # 只转发有内容的chunk
                if has_content:
                    # 转换为OpenAI标准格式
                    openai_chunk = self._convert_to_openai_format(chunk_dict)
                    # 零延迟转换和转发 - 保持SSE格式
                    sse_chunk = (
                        f"data: {json.dumps(openai_chunk, ensure_ascii=False)}\n\n"
                    )
                    yield sse_chunk
                else:
                    # 记录空chunk但不转发 - 显示详细信息用于调试
                    logger.debug(f"🔇 跳过空chunk #{chunk_count}: {chunk_dict}")

            total_time = time.time() - start_time
            logger.info(
                f"✅ Zhipu实时流式响应完成 - 总耗时: {total_time:.3f}秒，处理chunk: {chunk_count}"
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

            raise Exception(f"Zhipu stream API error: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Zhipu stream adapter error: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """Execute Zhipu health check - using OpenAI library"""
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
                    f"ZhipuAdapter health check successful - test chat completion"
                )
                self.health_status = HealthStatus.HEALTHY
                self.metrics.last_health_check = time.time()
                return HealthStatus.HEALTHY
            except Exception as e:
                logger.info(f"Test chat request failed: {str(e)}")

            # If all fail, mark as degraded
            logger.info(f"ZhipuAdapter health check failed, mark as degraded")
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
            raise Exception(f"Zhipu embedding creation error: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """Get available model list"""
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            return response.json().get("data", [])

        except Exception as e:
            raise Exception(f"Zhipu model list get error: {str(e)}")

    async def create_image(
        self,
        prompt: str,
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image from text prompt (Zhipu does not support image generation)"""
        raise NotImplementedError("Zhipu does not support image generation")

    async def edit_image(
        self,
        image: str,
        prompt: str,
        mask: Optional[str] = None,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Edit image based on prompt and optional mask (Zhipu does not support image editing)"""
        raise NotImplementedError("Zhipu does not support image editing")

    async def create_image_variation(
        self,
        image: str,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image variations from base image (Zhipu does not support image variations)"""
        raise NotImplementedError("Zhipu does not support image variations")
