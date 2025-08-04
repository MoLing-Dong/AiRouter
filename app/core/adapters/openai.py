import time
import uuid
from typing import Dict, List, Optional, Any
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import httpx
import json


class OpenAIAdapter(BaseAdapter):
    """OpenAI模型适配器"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        super().__init__(model_config, api_key)
        # OpenAI特定的配置
        self.api_version = "2024-02-15"
        self.client.headers.update({"OpenAI-Beta": "assistants=v1"})

    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """格式化消息为OpenAI格式"""
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
        """执行OpenAI聊天完成请求"""
        start_time = time.time()

        try:
            # 构建请求数据
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

            # 添加工具配置
            if request.tools:
                payload["tools"] = [tool.dict() for tool in request.tools]
                if request.tool_choice:
                    payload["tool_choice"] = request.tool_choice

            # 发送请求
            response = await self.client.post(
                f"{self.base_url}/chat/completions", json=payload
            )

            response.raise_for_status()
            response_data = response.json()

            # 计算响应时间
            response_time = time.time() - start_time

            # 更新指标
            tokens_used = response_data.get("usage", {}).get("total_tokens", 0)
            self.update_metrics(response_time, True, tokens_used)

            # 构建标准响应
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

            # 根据错误状态码更新健康状态
            if e.response.status_code >= 500:
                self.health_status = HealthStatus.UNHEALTHY
            elif e.response.status_code >= 400:
                self.health_status = HealthStatus.DEGRADED

            raise Exception(
                f"OpenAI API错误: {e.response.status_code} - {e.response.text}"
            )

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"OpenAI适配器错误: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """执行OpenAI健康检查"""
        try:
            # 使用更简单的健康检查方法 - 只检查API连接
            # 注意：某些第三方OpenAI兼容API可能不支持/models端点
            # 所以我们使用一个更通用的方法

            # 尝试获取模型列表
            try:
                response = await self.client.get(f"{self.base_url}/models")
                if response.status_code == 200:
                    self.health_status = HealthStatus.HEALTHY
                    self.metrics.last_health_check = time.time()
                    return HealthStatus.HEALTHY
            except:
                pass

            # 如果/models端点不可用，尝试简单的HEAD请求
            try:
                response = await self.client.head(f"{self.base_url}/chat/completions")
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
        """创建文本嵌入"""
        try:
            payload = {"model": "text-embedding-ada-002", "input": text}

            response = await self.client.post(
                f"{self.base_url}/embeddings", json=payload
            )

            response.raise_for_status()
            return response.json()

        except Exception as e:
            raise Exception(f"OpenAI嵌入创建错误: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表"""
        try:
            response = await self.client.get(f"{self.base_url}/models")
            response.raise_for_status()
            return response.json().get("data", [])

        except Exception as e:
            raise Exception(f"OpenAI模型列表获取错误: {str(e)}")
