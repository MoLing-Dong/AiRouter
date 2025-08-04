#!/usr/bin/env python3
"""
AI路由器API客户端示例
演示如何调用聊天完成接口
"""

import requests
import json
import time


class AIRouterClient:
    """AI路由器API客户端"""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    def chat_completion(self, model: str, messages: list, **kwargs):
        """发送聊天完成请求"""
        url = f"{self.base_url}/v1/chat/completions"

        payload = {"model": model, "messages": messages, **kwargs}

        response = requests.post(url, headers=self.headers, json=payload)
        response.raise_for_status()
        return response.json()

    def chat_completion_stream(self, model: str, messages: list, **kwargs):
        """发送流式聊天完成请求"""
        url = f"{self.base_url}/v1/chat/completions"

        payload = {"model": model, "messages": messages, "stream": True, **kwargs}

        response = requests.post(url, headers=self.headers, json=payload, stream=True)
        response.raise_for_status()
        return response

    def list_models(self):
        """获取可用模型列表"""
        url = f"{self.base_url}/v1/models"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def health_check(self):
        """健康检查"""
        url = f"{self.base_url}/v1/health"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()


def example_usage():
    """使用示例"""
    # 创建客户端
    client = AIRouterClient("http://localhost:8000")

    print("=== AI路由器API客户端示例 ===\n")

    # 1. 健康检查
    print("1. 健康检查:")
    try:
        health = client.health_check()
        print(f"   状态: {health['status']}")
        print(f"   模型状态: {health['models']}")
    except Exception as e:
        print(f"   健康检查失败: {e}")
    print()

    # 2. 获取模型列表
    print("2. 获取可用模型:")
    try:
        models = client.list_models()
        for model in models["data"]:
            print(f"   - {model['id']}")
    except Exception as e:
        print(f"   获取模型列表失败: {e}")
    print()

    # 3. 聊天完成请求
    print("3. 聊天完成请求:")
    try:
        messages = [
            {"role": "system", "content": "你是一个有用的AI助手。"},
            {"role": "user", "content": "你好，请介绍一下你自己。"},
        ]

        response = client.chat_completion(
            model="gpt-4",  # 使用配置的模型名称
            messages=messages,
            temperature=0.7,
            max_tokens=100,
        )

        print(f"   响应ID: {response['id']}")
        print(f"   模型: {response['model']}")
        print(f"   内容: {response['choices'][0]['message']['content']}")
        if response.get("usage"):
            print(f"   使用情况: {response['usage']}")

    except Exception as e:
        print(f"   聊天完成失败: {e}")
    print()

    # 4. 流式聊天完成
    print("4. 流式聊天完成:")
    try:
        messages = [{"role": "user", "content": "请用中文写一首短诗。"}]

        stream_response = client.chat_completion_stream(
            model="gpt-4", messages=messages, temperature=0.8, max_tokens=200
        )

        print("   流式响应:")
        for line in stream_response.iter_lines():
            if line:
                line = line.decode("utf-8")
                if line.startswith("data: "):
                    data = line[6:]  # 去掉 'data: ' 前缀
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        if "choices" in chunk and chunk["choices"]:
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                print(delta["content"], end="", flush=True)
                    except json.JSONDecodeError:
                        continue
        print()  # 换行

    except Exception as e:
        print(f"   流式聊天完成失败: {e}")


def openai_compatible_example():
    """OpenAI兼容的调用示例"""
    print("\n=== OpenAI兼容调用示例 ===\n")

    # 模拟OpenAI客户端的调用方式
    import openai

    # 配置客户端
    client = openai.AsyncOpenAI(
        api_key="your-api-key",  # 可选
        base_url="http://localhost:8000/v1",  # 指向AI路由器
    )

    print("OpenAI兼容客户端配置完成")
    print("可以使用标准的OpenAI客户端调用AI路由器API")


if __name__ == "__main__":
    example_usage()
    openai_compatible_example()
