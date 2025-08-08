import time
from typing import Dict, List, Any
from .base import BaseAdapter, ChatRequest, ChatResponse, Message, HealthStatus
import openai
from app.utils.logging_config import get_factory_logger

# 获取日志器
logger = get_factory_logger()


class VolcengineAdapter(BaseAdapter):
    """Volcengine模型适配器 - 使用OpenAI库"""

    def __init__(self, model_config: Dict[str, Any], api_key: str):
        super().__init__(model_config, api_key)
        # 确保base_url不以/结尾，避免OpenAI库自动添加路径
        base_url = self.base_url.rstrip("/")
        # 初始化OpenAI客户端
        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """格式化消息为OpenAI格式"""
        formatted_messages = []
        for msg in messages:
            formatted_msg = {"role": msg.role.value, "content": msg.content}
            if msg.name:
                formatted_msg["name"] = msg.name
            formatted_messages.append(formatted_msg)
        return formatted_messages

    async def chat_completion(self, request: ChatRequest) -> ChatResponse:
        """执行Volcengine聊天完成请求 - 使用OpenAI库"""
        start_time = time.time()

        try:
            # 构建请求参数
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

            # 过滤None值
            filtered_params = {k: v for k, v in params.items() if v is not None}

            # 使用OpenAI库发送请求
            response = await self.client.chat.completions.create(**filtered_params)

            # 计算响应时间
            response_time = time.time() - start_time

            # 更新指标
            tokens_used = response.usage.total_tokens if response.usage else 0
            self.update_metrics(response_time, True, tokens_used)

            # 构建标准响应 - 转换OpenAI对象为字典
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

            # 根据错误状态码更新健康状态
            if hasattr(e, "status_code"):
                if e.status_code >= 500:
                    self.health_status = HealthStatus.UNHEALTHY
                elif e.status_code >= 400:
                    self.health_status = HealthStatus.DEGRADED

            raise Exception(f"Volcengine API错误: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Volcengine适配器错误: {str(e)}")

    async def stream_chat_completion(self, request: ChatRequest):
        """执行Volcengine流式聊天完成请求 - 使用OpenAI库"""
        start_time = time.time()

        try:
            # 构建请求参数
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

            # 过滤None值
            filtered_params = {k: v for k, v in params.items() if v is not None}

            # 使用OpenAI库发送流式请求
            stream = await self.client.chat.completions.create(**filtered_params)

            # 直接返回原生的流式响应
            async for chunk in stream:
                logger.info(f"流式响应块: {chunk.model_dump_json()}")
                # 将JSON转换为SSE格式
                yield f"data: {chunk.model_dump_json()}\n\n"

            # 更新指标
            response_time = time.time() - start_time
            self.update_metrics(response_time, True)

        except openai.APIError as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)

            # 根据错误状态码更新健康状态
            if hasattr(e, "status_code"):
                if e.status_code >= 500:
                    self.health_status = HealthStatus.UNHEALTHY
                elif e.status_code >= 400:
                    self.health_status = HealthStatus.DEGRADED

            raise Exception(f"Volcengine流式API错误: {str(e)}")

        except Exception as e:
            response_time = time.time() - start_time
            self.update_metrics(response_time, False)
            self.health_status = HealthStatus.UNHEALTHY
            raise Exception(f"Volcengine流式适配器错误: {str(e)}")

    async def health_check(self) -> HealthStatus:
        """执行Volcengine健康检查 - 使用OpenAI库"""
        try:

            # 尝试简单的聊天请求
            try:
                # 发送一个简单的测试请求
                test_response = await self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "test"}],
                    max_tokens=1,
                )
                logger.info(f"VolcengineAdapter健康检查成功 - 测试聊天完成")
                self.health_status = HealthStatus.HEALTHY
                self.metrics.last_health_check = time.time()
                return HealthStatus.HEALTHY
            except Exception as e:
                logger.info(f"测试聊天请求失败: {str(e)}")

            # 如果都失败了，标记为降级
            logger.info(f"VolcengineAdapter健康检查失败，标记为降级")
            self.health_status = HealthStatus.DEGRADED
            return HealthStatus.DEGRADED

        except openai.AuthenticationError:
            # 认证错误
            self.health_status = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY
        except openai.APIError as e:
            # API错误
            if hasattr(e, "status_code") and e.status_code == 401:
                self.health_status = HealthStatus.UNHEALTHY
            else:
                self.health_status = HealthStatus.DEGRADED
            return self.health_status
        except Exception as e:
            # 其他错误
            self.health_status = HealthStatus.UNHEALTHY
            return HealthStatus.UNHEALTHY

    async def create_embedding(self, text: str) -> Dict[str, Any]:
        """创建文本嵌入 - 使用OpenAI库"""
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
            raise Exception(f"Volcengine嵌入创建错误: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """获取可用模型列表 - 使用OpenAI库"""
        try:
            response = await self.client.models.list()
            return [model.model_dump() for model in response.data]

        except Exception as e:
            raise Exception(f"Volcengine模型列表获取错误: {str(e)}")
