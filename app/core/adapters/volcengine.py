import time
from typing import Dict, List, Any
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
        # Initialize OpenAI client
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

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
                "stream": True,  # 强制启用流式
            }

            # Filter None values
            filtered_params = {k: v for k, v in params.items() if v is not None}

            # Use OpenAI library to send streaming request
            stream = await self.client.chat.completions.create(**filtered_params)

            # Directly return native streaming response
            async for chunk in stream:
                # Convert JSON to SSE format
                yield f"data: {chunk.model_dump_json()}\n\n"

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

            raise Exception(f"Volcengine stream API error: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
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
                logger.info(f"VolcengineAdapter health check successful - test chat completion")
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
