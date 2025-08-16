import time
import uuid
from typing import Dict, List, Optional, Any
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import httpx
import json
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


class OpenAIAdapter(BaseAdapter):
    """OpenAI model adapter"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        super().__init__(model_config, api_key)
        # OpenAI specific configuration
        self.api_version = "2024-02-15"
        self.client.headers.update({"OpenAI-Beta": "assistants=v1"})

    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """Format messages to OpenAI format"""
        formatted_messages = []
        for msg in messages:
            formatted_msg = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                formatted_msg["name"] = msg.name
            if msg.function_call:
                formatted_msg["function_call"] = msg.function_call
            formatted_messages.append(formatted_msg)
        return formatted_messages

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """Execute OpenAI chat completion request"""
        start_time = time.time()

        try:
            # Build request data
            payload = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stream": request.stream,
            }

            # Add tool configuration
            if request.tools:
                payload["tools"] = [tool.dict() for tool in request.tools]
                if request.tool_choice:
                    payload["tool_choice"] = request.tool_choice

            # Send request
            response = await self.client.post(
                f"{self.base_url}/chat/completions", json=payload
            )

            response.raise_for_status()
            response_data = response.json()

            # Calculate response time
            response_time = time.time() - start_time

            # Update metrics
            tokens_used = response_data.get("usage", {}).get("total_tokens", 0)
            self.update_metrics(response_time, True, tokens_used)

            # Build standard response
            chat_response = ChatResponse(
                id=response_data.get("id", str(uuid.uuid4())),
                created=int(time.time()),
                model=self.model_name,
                choices=response_data.get("choices", []),
                usage=response_data.get("usage"),
                system_fingerprint=response_data.get("system_fingerprint"),
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
                f"OpenAI API error: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY

            # Sync health status to database
            self.sync_health_status_to_database("unhealthy", str(e))

            raise Exception(f"OpenAI adapter error: {str(e)}")

    async def stream_chat_completion(self, request: ChatRequest):
        """Execute OpenAI stream chat completion request"""
        start_time = time.time()

        try:
            # Build request data
            payload = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "temperature": request.temperature,
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "top_p": request.top_p,
                "frequency_penalty": request.frequency_penalty,
                "presence_penalty": request.presence_penalty,
                "stream": True,  # Force enable streaming
            }

            # Add tool configuration
            if request.tools:
                payload["tools"] = [tool.dict() for tool in request.tools]
                if request.tool_choice:
                    payload["tool_choice"] = request.tool_choice

            # Try using OpenAI library streaming (if available)
            try:
                # Create OpenAI client
                import openai

                openai_client = openai.AsyncOpenAI(
                    api_key=self.api_key, base_url=self.base_url
                )

                # Use OpenAI library to send streaming request
                stream = await openai_client.chat.completions.create(**payload)

                # Process streaming response chunk by chunk
                async for chunk in stream:
                    # Convert JSON to SSE format
                    yield f"data: {chunk.model_dump_json()}\n\n"

            except Exception as openai_error:
                logger.info(
                    f"OpenAI library streaming failed, fallback to httpx: {openai_error}"
                )

                # Fallback to httpx streaming
                async with self.client.stream(
                    "POST", f"{self.base_url}/chat/completions", json=payload
                ) as response:
                    response.raise_for_status()

                    # Process streaming response line by line
                    async for line in response.aiter_lines():
                        if line.strip():  # Ignore empty line
                            logger.info(f"OpenAI streaming response: {line}")
                            # Ensure each line has correct format and newline
                            if not line.startswith("data: "):
                                line = "data: " + line
                            yield line + "\n"

            # Send end marker
            yield "data: [DONE]\n\n"

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
                f"OpenAI stream API error: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"OpenAI stream adapter error: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """Execute health check"""
        try:
            # Try to get model list
            try:
                start_time = time.time()
                response = await self.client.get(f"{self.base_url}/models")
                response_time = time.time() - start_time

                if response.status_code == 200:
                    logger.info(
                        "OpenAIAdapter health check successful - get model list"
                    )
                    self.health_status = HealthStatus.HEALTHY
                    self.metrics.last_health_check = time.time()

                    # Sync health status to database
                    self.sync_health_status_to_database("healthy")

                    return HealthStatus.HEALTHY
            except:
                pass

            # If /models endpoint is not available, try simple HEAD request
            try:
                start_time = time.time()
                response = await self.client.head(f"{self.base_url}/chat/completions")
                response_time = time.time() - start_time

                if response.status_code in [
                    200,
                    405,
                ]:  # 405 means method not allowed, but endpoint exists
                    logger.info("OpenAI health check successful - simple HEAD request")
                    self.health_status = HealthStatus.HEALTHY
                    self.metrics.last_health_check = time.time()

                    # Sync health status to database
                    self.sync_health_status_to_database("healthy")

                    return HealthStatus.HEALTHY
            except:
                pass

            # If all fail, mark as degraded
            self.health_status = HealthStatus.DEGRADED

            # Sync health status to database
            self.sync_health_status_to_database("degraded")

            return HealthStatus.DEGRADED

        except httpx.ConnectError:
            # Connection error
            self.health_status = HealthStatus.UNHEALTHY

            # Sync health status to database
            self.sync_health_status_to_database("unhealthy")

            return HealthStatus.UNHEALTHY
        except httpx.HTTPStatusError as e:
            # HTTP error
            if e.response.status_code == 401:
                # Authentication error
                self.health_status = HealthStatus.UNHEALTHY
            else:
                self.health_status = HealthStatus.DEGRADED

            # Sync health status to database
            self.sync_health_status_to_database(
                self._convert_health_status(self.health_status)
            )

            return self.health_status
        except Exception as e:
            # Other error
            self.health_status = HealthStatus.UNHEALTHY

            # Sync health status to database
            self.sync_health_status_to_database("unhealthy")

            return HealthStatus.UNHEALTHY

    async def create_embedding(self, text: str) -> Dict[str, Any]:
        """Create text embedding"""
        try:
            payload = {"model": "text-embedding-ada-002", "input": text}

            response = await self.client.post(
                f"{self.base_url}/embeddings", json=payload
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            raise Exception(f"OpenAI embedding creation error: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """Get available model list"""
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            return response.json().get("data", [])

        except Exception as e:
            raise Exception(f"OpenAI model list get error: {str(e)}")

    async def create_image(
        self,
        prompt: str,
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        style: str = "vivid",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image from text prompt using OpenAI DALL-E API"""
        try:
            payload = {
                "prompt": prompt,
                "n": n,
                "size": size,
                "response_format": response_format,
            }

            # Add quality and style for DALL-E 3
            if "dall-e-3" in self.model_name.lower():
                payload["quality"] = quality
                payload["style"] = style

            response = await self.client.post(
                f"{self.base_url}/images/generations", json=payload
            )

            response.raise_for_status()
            response_data = response.json()

            return response_data.get("data", [])

        except Exception as e:
            raise Exception(f"OpenAI image generation error: {str(e)}")

    async def edit_image(
        self,
        image: str,
        prompt: str,
        mask: Optional[str] = None,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Edit image based on prompt and optional mask using OpenAI DALL-E API"""
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

            response = await self.client.post(
                f"{self.base_url}/images/edits", json=payload
            )

            response.raise_for_status()
            response_data = response.json()

            return response_data.get("data", [])

        except Exception as e:
            raise Exception(f"OpenAI image editing error: {str(e)}")

    async def create_image_variation(
        self,
        image: str,
        n: int = 1,
        size: str = "1024x1024",
        response_format: str = "url",
    ) -> List[Dict[str, Any]]:
        """Create image variations from base image using OpenAI DALL-E API"""
        try:
            payload = {
                "image": image,
                "n": n,
                "size": size,
                "response_format": response_format,
            }

            response = await self.client.post(
                f"{self.base_url}/images/variations", json=payload
            )

            response.raise_for_status()
            response_data = response.json()

            return response_data.get("data", [])

        except Exception as e:
            raise Exception(f"OpenAI image variation creation error: {str(e)}")
