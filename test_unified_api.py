#!/usr/bin/env python3
"""
测试统一模型API接口的脚本
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_unified_models_api():
    """测试统一的模型API接口"""
    
    print("🧪 测试统一模型API接口")
    print("=" * 50)
    
    # 测试1: 获取所有模型
    print("\n1️⃣ 测试获取所有模型")
    print("GET /v1/models/")
    try:
        response = requests.get(f"{BASE_URL}/v1/models/")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 成功获取 {len(models.get('data', []))} 个模型")
            for model in models.get('data', [])[:3]:  # 只显示前3个
                print(f"   - {model['id']} (能力数: {model['capabilities_count']})")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 测试2: 获取聊天模型
    print("\n2️⃣ 测试获取聊天模型")
    print("GET /v1/models/?capabilities=TEXT,MULTIMODAL_IMAGE_UNDERSTANDING")
    try:
        response = requests.get(f"{BASE_URL}/v1/models/?capabilities=TEXT,MULTIMODAL_IMAGE_UNDERSTANDING")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 成功获取 {len(models.get('data', []))} 个聊天模型")
            for model in models.get('data', []):
                print(f"   - {model['id']} (能力数: {model['capabilities_count']})")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 测试3: 获取图片生成模型
    print("\n3️⃣ 测试获取图片生成模型")
    print("GET /v1/models/?capabilities=MULTIMODAL_TEXT_TO_IMAGE,MULTIMODAL_IMAGE_TO_IMAGE")
    try:
        response = requests.get(f"{BASE_URL}/v1/models/?capabilities=MULTIMODAL_TEXT_TO_IMAGE,MULTIMODAL_IMAGE_TO_IMAGE")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 成功获取 {len(models.get('data', []))} 个图片生成模型")
            for model in models.get('data', []):
                print(f"   - {model['id']} (能力数: {model['capabilities_count']})")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 测试4: 获取纯文本模型
    print("\n4️⃣ 测试获取纯文本模型")
    print("GET /v1/models/?capabilities=TEXT")
    try:
        response = requests.get(f"{BASE_URL}/v1/models/?capabilities=TEXT")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 成功获取 {len(models.get('data', []))} 个纯文本模型")
            for model in models.get('data', []):
                print(f"   - {model['id']} (能力数: {model['capabilities_count']})")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")
    
    # 测试5: 测试无效的能力参数
    print("\n5️⃣ 测试无效的能力参数")
    print("GET /v1/models/?capabilities=INVALID_CAPABILITY")
    try:
        response = requests.get(f"{BASE_URL}/v1/models/?capabilities=INVALID_CAPABILITY")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 成功获取 {len(models.get('data', []))} 个模型 (无效能力被忽略)")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

def test_chat_api_filtering():
    """测试聊天API的自动模型过滤"""
    
    print("\n\n🧪 测试聊天API自动模型过滤")
    print("=" * 50)
    
    # 测试聊天完成API
    print("\n1️⃣ 测试聊天完成API")
    print("POST /v1/chat/completions")
    
    chat_data = {
        "model": "gpt-4",  # 假设这个模型存在
        "messages": [
            {"role": "user", "content": "Hello, how are you?"}
        ],
        "temperature": 0.7
    }
    
    try:
        response = requests.post(f"{BASE_URL}/v1/chat/completions", json=chat_data)
        if response.status_code == 200:
            print("✅ 聊天API调用成功")
        elif response.status_code == 400:
            result = response.json()
            if "not available" in result.get("detail", ""):
                print("✅ 聊天API正确过滤了不支持的模型")
            else:
                print(f"❌ 其他错误: {result}")
        else:
            print(f"❌ 失败: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ 请求异常: {e}")

if __name__ == "__main__":
    print("🚀 AI路由器统一模型API测试")
    print("请确保服务已启动在 http://localhost:8000")
    
    try:
        test_unified_models_api()
        test_chat_api_filtering()
        
        print("\n" + "=" * 50)
        print("🎉 测试完成!")
        print("\n💡 使用说明:")
        print("1. 获取所有模型: GET /v1/models/")
        print("2. 获取聊天模型: GET /v1/models/?capabilities=TEXT,MULTIMODAL_IMAGE_UNDERSTANDING")
        print("3. 获取图片模型: GET /v1/models/?capabilities=MULTIMODAL_TEXT_TO_IMAGE,MULTIMODAL_IMAGE_TO_IMAGE")
        print("4. 获取文本模型: GET /v1/models/?capabilities=TEXT")
        
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n❌ 测试过程中发生错误: {e}")
