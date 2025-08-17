#!/usr/bin/env python3
"""
测试模型创建与供应商关联功能
"""

import requests
import json
import sys

# 配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/v1/db"

def test_create_provider():
    """测试创建供应商"""
    print("🔧 创建测试供应商...")
    
    provider_data = {
        "name": "OpenAI Test",
        "provider_type": "openai",
        "description": "测试用的OpenAI供应商",
        "is_enabled": True
    }
    
    try:
        response = requests.post(f"{API_BASE}/providers", json=provider_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 供应商创建成功: {result['provider_name']} (ID: {result['provider_id']})")
            return result['provider_id']
        else:
            print(f"❌ 供应商创建失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建供应商时出错: {e}")
        return None

def test_create_model_with_provider(provider_id):
    """测试创建模型并关联供应商"""
    print(f"\n🚀 创建模型并关联供应商 (ID: {provider_id})...")
    
    model_data = {
        "name": "gpt-4-test",
        "llm_type": "chat",
        "description": "测试用的GPT-4模型",
        "provider_id": provider_id,
        "provider_weight": 15,
        "is_provider_preferred": True
    }
    
    try:
        response = requests.post(f"{API_BASE}/models", json=model_data)
        if response.status_code == 200:
            result = response.json()
            print(f"✅ 模型创建成功: {result['name']} (ID: {result['id']})")
            if 'provider_info' in result:
                provider_info = result['provider_info']
                print(f"   📍 供应商关联: {provider_info['provider_name']} (权重: {provider_info['weight']}, 优先: {provider_info['is_preferred']})")
            return result['id']
        else:
            print(f"❌ 模型创建失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建模型时出错: {e}")
        return None

def main():
    """主测试函数"""
    print("🧪 开始测试模型创建与供应商关联功能...")
    print("=" * 60)
    
    # 测试1: 创建供应商
    provider_id = test_create_provider()
    if not provider_id:
        print("❌ 无法继续测试，供应商创建失败")
        sys.exit(1)
    
    # 测试2: 创建模型并关联供应商
    model_id = test_create_model_with_provider(provider_id)
    
    print("\n" + "=" * 60)
    if model_id:
        print("🎉 测试通过！")
        print(f"   - 带供应商关联的模型: {model_id}")
    else:
        print("⚠️  测试失败，请检查日志")

if __name__ == "__main__":
    main()
