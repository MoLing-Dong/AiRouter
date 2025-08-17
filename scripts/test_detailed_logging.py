#!/usr/bin/env python3
"""
测试详细的日志记录功能
"""

import requests
import json
import sys
import time

# 配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/v1/db"


def test_create_provider_with_detailed_logging():
    """测试创建供应商的详细日志"""
    print("🔧 测试创建供应商的详细日志...")

    provider_data = {
        "name": "OpenAI Test Logging",
        "provider_type": "openai",
        "description": "测试详细日志记录的OpenAI供应商",
        "is_enabled": True,
    }

    try:
        print(f"   📤 发送请求: POST {API_BASE}/providers")
        print(
            f"   📋 请求数据: {json.dumps(provider_data, indent=2, ensure_ascii=False)}"
        )

        response = requests.post(f"{API_BASE}/providers", json=provider_data)

        print(f"   📥 响应状态: {response.status_code}")
        print(f"   📋 响应内容: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print(
                f"✅ 供应商创建成功: {result['provider_name']} (ID: {result['provider_id']})"
            )
            return result["provider_id"]
        else:
            print(f"❌ 供应商创建失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建供应商时出错: {e}")
        return None


def test_create_model_with_provider_detailed_logging(provider_id):
    """测试创建模型并关联供应商的详细日志"""
    print(f"\n🚀 测试创建模型并关联供应商的详细日志 (供应商ID: {provider_id})...")

    model_data = {
        "name": "gpt-4-test-logging",
        "llm_type": "chat",
        "description": "测试详细日志记录的GPT-4模型",
        "provider_id": provider_id,
        "provider_weight": 20,
        "is_provider_preferred": True,
    }

    try:
        print(f"   📤 发送请求: POST {API_BASE}/models")
        print(f"   📋 请求数据: {json.dumps(model_data, indent=2, ensure_ascii=False)}")

        response = requests.post(f"{API_BASE}/models", json=model_data)

        print(f"   📥 响应状态: {response.status_code}")
        print(f"   📋 响应内容: {response.text}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ 模型创建成功: {result['name']} (ID: {result['id']})")
            if "provider_info" in result:
                provider_info = result["provider_info"]
                print(
                    f"   📍 供应商关联: {provider_info['provider_name']} (权重: {provider_info['weight']}, 优先: {provider_info['is_preferred']})"
                )
            return result["id"]
        else:
            print(f"❌ 模型创建失败: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"❌ 创建模型时出错: {e}")
        return None


def test_error_scenario_detailed_logging():
    """测试错误场景的详细日志"""
    print(f"\n🚨 测试错误场景的详细日志...")

    # 尝试创建已存在的模型名称
    model_data = {
        "name": "gpt-4-test-logging",  # 使用已存在的名称
        "llm_type": "chat",
        "description": "测试重复名称的错误日志",
    }

    try:
        print(f"   📤 发送请求: POST {API_BASE}/models (预期失败)")
        print(f"   📋 请求数据: {json.dumps(model_data, indent=2, ensure_ascii=False)}")

        response = requests.post(f"{API_BASE}/models", json=model_data)

        print(f"   📥 响应状态: {response.status_code}")
        print(f"   📋 响应内容: {response.text}")

        if response.status_code == 400:
            print("✅ 错误场景测试成功 - 正确返回400状态码")
        else:
            print(f"⚠️ 意外响应: {response.status_code}")

    except Exception as e:
        print(f"❌ 错误场景测试时出错: {e}")


def test_invalid_provider_id_detailed_logging():
    """测试无效供应商ID的详细日志"""
    print(f"\n🚨 测试无效供应商ID的详细日志...")

    # 使用不存在的供应商ID
    model_data = {
        "name": "test-invalid-provider",
        "llm_type": "chat",
        "description": "测试无效供应商ID的错误日志",
        "provider_id": 99999,  # 不存在的ID
        "provider_weight": 10,
        "is_provider_preferred": False,
    }

    try:
        print(f"   📤 发送请求: POST {API_BASE}/models (预期失败)")
        print(f"   📋 请求数据: {json.dumps(model_data, indent=2, ensure_ascii=False)}")

        response = requests.post(f"{API_BASE}/models", json=model_data)

        print(f"   📥 响应状态: {response.status_code}")
        print(f"   📋 响应内容: {response.text}")

        if response.status_code == 500:
            print("✅ 无效供应商ID测试成功 - 正确返回500状态码")
        else:
            print(f"⚠️ 意外响应: {response.status_code}")

    except Exception as e:
        print(f"❌ 无效供应商ID测试时出错: {e}")


def main():
    """主测试函数"""
    print("🧪 开始测试详细的日志记录功能...")
    print("=" * 80)

    # 测试1: 创建供应商
    provider_id = test_create_provider_with_detailed_logging()
    if not provider_id:
        print("❌ 无法继续测试，供应商创建失败")
        sys.exit(1)

    # 等待一下，确保日志有时间写入
    time.sleep(1)

    # 测试2: 创建模型并关联供应商
    model_id = test_create_model_with_provider_detailed_logging(provider_id)

    # 等待一下，确保日志有时间写入
    time.sleep(1)

    # 测试3: 测试错误场景
    test_error_scenario_detailed_logging()

    # 等待一下，确保日志有时间写入
    time.sleep(1)

    # 测试4: 测试无效供应商ID
    test_invalid_provider_id_detailed_logging()

    print("\n" + "=" * 80)
    if model_id:
        print("🎉 详细日志测试完成！")
        print(f"   - 成功创建的模型: {model_id}")
        print(f"   - 成功创建的供应商: {provider_id}")
        print("\n💡 现在请检查日志文件，应该能看到详细的日志记录:")
        print("   - 事务开始和结束时间")
        print("   - 每个验证步骤的详细信息")
        print("   - 错误发生时的完整堆栈跟踪")
        print("   - 性能指标（执行时间等）")
    else:
        print("⚠️ 部分测试失败，请检查日志")

    print("\n📁 日志文件位置:")
    print("   - 应用日志: logs/ai_router_YYYYMMDD.log")
    print("   - 错误日志: logs/ai_router_error_YYYYMMDD.log")


if __name__ == "__main__":
    main()
