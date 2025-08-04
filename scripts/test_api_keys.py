#!/usr/bin/env python3
"""
测试API密钥读取
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def test_api_keys_from_settings():
    """测试从settings读取API密钥"""
    print("🔧 测试API密钥读取...")

    api_keys = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY",
        "AZURE_API_KEY",
        "THIRD_PARTY_API_KEY",
        "PRIVATE_API_KEY",
    ]

    for key in api_keys:
        value = getattr(settings, key, "")
        if value:
            print(f"  ✅ {key}: {value[:10]}...")
        else:
            print(f"  ⚠️  {key}: 未设置")

    print("\n✅ API密钥读取测试完成!")


def test_api_key_fallback():
    """测试API密钥备用机制"""
    print("\n🔧 测试API密钥备用机制...")

    # 模拟适配器管理器中的API密钥获取逻辑
    def get_api_key_for_provider(provider_name: str) -> str:
        from config.settings import settings

        # 尝试从settings获取API密钥
        api_key_attr = f"{provider_name.upper().replace('-', '_')}_API_KEY"
        api_key = getattr(settings, api_key_attr, "")

        if not api_key:
            # 尝试其他常见的API密钥属性名
            common_attrs = [
                f"{provider_name.upper()}_API_KEY",
                f"{provider_name.replace('-', '_').upper()}_API_KEY",
                f"{provider_name.replace('-', '').upper()}_API_KEY",
            ]

            for attr in common_attrs:
                api_key = getattr(settings, attr, "")
                if api_key:
                    break

        return api_key

    providers = ["openai", "anthropic", "google", "azure-openai", "third-party"]

    for provider in providers:
        api_key = get_api_key_for_provider(provider)
        if api_key:
            print(f"  ✅ {provider}: {api_key[:10]}...")
        else:
            print(f"  ⚠️  {provider}: 未找到API密钥")

    print("✅ API密钥备用机制测试完成!")


if __name__ == "__main__":
    print("🚀 开始API密钥读取测试...\n")

    test_api_keys_from_settings()
    test_api_key_fallback()

    print("\n🎉 API密钥读取测试完成!")
