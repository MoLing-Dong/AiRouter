import time
import uuid
from typing import Dict, List, Optional, Any
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import httpx
import json


class AnthropicAdapter(BaseAdapter):
    """Anthropic Claude模型适配器"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        super().__init__(model_config, api_key)
        # Anthropic特定的配置
        self.client.headers.update(
            {"anthropic-version": "2023-06-01", "x-api-key": api_key}
        )
        # 移除Bearer前缀，Anthropic使用x-api-key
        self.client.headers.pop("Authorization", None)

    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """格式化消息为Anthropic格式"""
        formatted_messages = []
        for msg in messages:
            formatted_msg = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                formatted_msg["name"] = msg.name
            formatted_messages.append(formatted_msg)
        return formatted_messages

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """执行Anthropic聊天完成请求"""
        start_time = time.time()

        try:
            # 构建请求数据
            payload = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": request.stream,
            }

            # Anthropic不支持frequency_penalty和presence_penalty
            # 也不支持tools，需要特殊处理

            # 发送请求
            response = await self.client.post(
                f"{self.base_url}/v1/messages", json=payload
            )

            response.raise_for_status()
            response_data = response.json()

            # 计算响应时间
            response_time = time.time() - start_time

            # 更新指标
            tokens_used = response_data.get("usage", {}).get(
                "input_tokens", 0
            ) + response_data.get("usage", {}).get("output_tokens", 0)
            self.update_metrics(response_time, True, tokens_used)

            # 构建标准响应格式
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

            # 根据错误状态码更新健康状态
            if e.response.status_code >= 500:
                self.health_status = HealthStatus.UNHEALTHY
            elif e.response.status_code >= 400:
                self.health_status = HealthStatus.DEGRADED

            raise Exception(
                f"Anthropic API错误: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Anthropic适配器错误: {str(e)}")

    async def stream_chat_completion(self, request: ChatRequest):
        """执行Anthropic流式聊天完成请求"""
        start_time = time.time()

        try:
            # 构建请求数据
            payload = {
                "model": self.model_name,
                "messages": self.format_messages(request.messages),
                "max_tokens": request.max_tokens
                or self.model_config.get("max_tokens", 4096),
                "temperature": request.temperature,
                "top_p": request.top_p,
                "stream": True,  # 强制启用流式
            }

            # 发送流式请求
            async with self.client.stream(
                "POST", f"{self.base_url}/v1/messages", json=payload
            ) as response:
                response.raise_for_status()

                # 直接返回原生的流式响应
                async for line in response.aiter_lines():
                    yield line

            # 更新指标
            response_time = time.time() - start_time
            self.update_metrics(response_time, True)

        except httpx.HTTPStatusError as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)

            # 根据错误状态码更新健康状态
            if e.response.status_code >= 500:
                self.health_status = HealthStatus.UNHEALTHY
            elif e.response.status_code >= 400:
                self.health_status = HealthStatus.DEGRADED

            raise Exception(
                f"Anthropic流式API错误: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Anthropic流式适配器错误: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """执行Anthropic健康检查"""
        try:
            # 使用更简单的健康检查方法 - 只检查API连接
            # Anthropic支持/models端点，但我们也提供备用方案

            # 尝试获取模型列表
            try:
                response = await self.client.get(f"{self.base_url}/v1/models")
                if response.status_code == 200:
                    self.health_status = HealthStatus.HEALTHY
                    self.metrics.last_health_check = time.time()
                    return HealthStatus.HEALTHY
            except:
                pass

            # 如果/models端点不可用，尝试简单的HEAD请求
            try:
                response = await self.client.head(f"{self.base_url}/v1/messages")
                if response.status_code in [200, 405]:  # 405表示方法不允许，但端点存在
                    self.health_status = HealthStatus.HEALTHY
                    self.metrics.last_health_check = time.time()
                    return HealthStatus.HEALTHY
            except:
                pass

            # 如果都失败了，标记为降级
            self.health_status = HealthStatus.DEGRADED
            return HealthStatus.DEGRADED

        except httpx.ConnectError:
            # 连接错误
            self.health_status = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY
        except httpx.HTTPStatusError as e:
            # HTTP错误
            if e.response.status_code == 401:
                # 认证错误
                self.health_status = HealthStatus.UNHEALTHY
            else:
                self.health_status = HealthStatus.DEGRADED
            return self.health_status
        except Exception as e:
            # 其他错误
            self.health_status = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY

    async def create_embedding(self, text: str) -> Dict[str, Any]:
        """创建文本嵌入（Anthropic暂不支持）"""
        raise NotImplementedError("Anthropic暂不支持文本嵌入功能")

    async def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        try:
            response = await self.client.get(f"{self.base_url}/v1/models")
            response.raise_for_status()
            return response.json().get("data", [])

        except Exception as e:
            raise Exception(f"Anthropic模型列表获取错误: {str(e)}")
