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
        # Anthropic specific configuration
        self.client.headers.update(
            {"anthropic-version": "2023-06-01", "x-api-key": api_key}
        )
        # Remove Bearer prefix, Anthropic uses x-api-key
        self.client.headers.pop("Authorization", None)

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
                "stream": True,  # Force enable streaming
            }

            # Send streaming request
            async with self.client.stream(
                "POST", f"{self.base_url}/v1/messages", json=payload
            ) as response:
                response.raise_for_status()

                # Directly return the native streaming response
                async for line in response.aiter_lines():
                    yield line

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
        """Execute Anthropic health check"""
        try:
            # Use simpler health check method - only check API connection
            # Anthropic supports /models endpoint, but we also provide fallback

            # Try to get model list
            try:
                response = await self.client.get(f"{self.base_url}/v1/models")
                if response.status_code == 200:
                    self.health_status = HealthStatus.HEALTHY
                    self.metrics.last_health_check = time.time()
                    return HealthStatus.HEALTHY
            except:
                pass

            # If /models endpoint is not available, try simple HEAD request
            try:
                response = await self.client.head(f"{self.base_url}/v1/messages")
                if response.status_code in [
                    200,
                    405,
                ]:  # 405 means method not allowed, but endpoint exists
                    self.health_status = HealthStatus.HEALTHY
                    self.metrics.last_health_check = time.time()
                    return HealthStatus.HEALTHY
            except:
                pass

            # If all fail, mark as degraded
            self.health_status = HealthStatus.DEGRADED
            return HealthStatus.DEGRADED

        except httpx.ConnectError:
            # Connection error
            self.health_status = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY
        except httpx.HTTPStatusError as e:
            # HTTP error
            if e.response.status_code == 401:
                # Authentication error
                self.health_status = HealthStatus.UNHEALTHY
            else:
                self.health_status = HealthStatus.DEGRADED
            return self.health_status
        except Exception as e:
            # Other error
            self.health_status = HealthStatus.UNHEALTHY
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
