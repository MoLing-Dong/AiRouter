#!/usr/bin/env python3
"""
测试环境变量读取机制
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings, LoadBalancingConfig, Settings


def test_direct_env_vars():
    """测试直接环境变量读取"""
    print("🔧 测试直接环境变量读取...")

    print(f"📊 APP_NAME: {settings.APP_NAME}")
    print(f"🌐 HOST: {settings.HOST}")
    print(f"🔌 PORT: {settings.PORT}")
    print(f"🐛 DEBUG: {settings.DEBUG}")
    print(f"🗄️  DATABASE_URL: {settings.DATABASE_URL}")

    # 检查环境变量
    env_vars = ["APP_NAME", "HOST", "PORT", "DEBUG", "DATABASE_URL"]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: 未设置 (使用默认值)")


def test_prefixed_env_vars():
    """测试前缀环境变量读取"""
    print("\n🔧 测试前缀环境变量读取...")

    lb_config = LoadBalancingConfig()
    print(f"📊 策略: {lb_config.strategy}")
    print(f"⏱️  健康检查间隔: {lb_config.health_check_interval}")
    print(f"🔄 最大重试次数: {lb_config.max_retries}")

    # 检查环境变量
    env_vars = [
        "LOAD_BALANCING_STRATEGY",
        "LOAD_BALANCING_HEALTH_CHECK_INTERVAL",
        "LOAD_BALANCING_MAX_RETRIES",
    ]
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"  ✅ {var}: {value}")
        else:
            print(f"  ⚠️  {var}: 未设置 (使用默认值)")


def test_env_priority():
    """测试环境变量优先级"""
    print("\n🔧 测试环境变量优先级...")

    # 设置一些测试环境变量
    test_env = {"APP_NAME": "测试应用", "LOAD_BALANCING_STRATEGY": "round_robin"}

    # 临时设置环境变量
    original_env = {}
    for key, value in test_env.items():
        original_env[key] = os.getenv(key)
        os.environ[key] = value

    try:
        # 重新创建配置实例
        from config.settings import Settings

        test_settings = Settings()
        test_lb_config = LoadBalancingConfig()

        print(f"📊 环境变量优先级测试:")
        print(f"  APP_NAME: {test_settings.APP_NAME}")
        print(f"  LOAD_BALANCING_STRATEGY: {test_lb_config.strategy}")

    finally:
        # 恢复原始环境变量
        for key, value in original_env.items():
            if value is not None:
                os.environ[key] = value
            else:
                os.environ.pop(key, None)


def test_env_file_support():
    """测试.env文件支持"""
    print("\n🔧 测试.env文件支持...")

    # 检查是否存在.env文件
    env_file = Path(project_root) / ".env"
    if env_file.exists():
        print(f"✅ 找到.env文件: {env_file}")
        with open(env_file, "r") as f:
            lines = f.readlines()
            print(f"📄 .env文件包含 {len(lines)} 行配置")
    else:
        print(f"⚠️  未找到.env文件: {env_file}")

    print(f"📋 Settings类配置:")
    print(f"  env_file: {Settings.Config.env_file}")
    print(f"  case_sensitive: {Settings.Config.case_sensitive}")
    print(f"  extra: {Settings.Config.extra}")


if __name__ == "__main__":
    print("🚀 开始环境变量读取测试...\n")

    test_direct_env_vars()
    test_prefixed_env_vars()
    test_env_priority()
    test_env_file_support()

    print("\n🎉 环境变量读取测试完成!")
