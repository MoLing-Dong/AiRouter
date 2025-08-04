#!/usr/bin/env python3
"""
测试负载均衡环境变量配置
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import settings


def test_load_balancing_config():
    """测试负载均衡配置"""
    print("🔧 测试负载均衡配置...")

    # 获取负载均衡配置
    lb_config = settings.LOAD_BALANCING

    print(f"📊 当前负载均衡策略: {lb_config.strategy}")
    print(f"⏱️  健康检查间隔: {lb_config.health_check_interval} 秒")
    print(f"🔄 最大重试次数: {lb_config.max_retries}")
    print(f"⏰ 超时时间: {lb_config.timeout} 秒")
    print(f"🛡️  启用故障转移: {lb_config.enable_fallback}")
    print(f"💰 启用成本优化: {lb_config.enable_cost_optimization}")

    # 检查环境变量
    print("\n🔍 检查环境变量:")
    env_vars = [
        "LOAD_BALANCING_STRATEGY",
        "LOAD_BALANCING_HEALTH_CHECK_INTERVAL",
        "LOAD_BALANCING_MAX_RETRIES",
        "LOAD_BALANCING_TIMEOUT",
        "LOAD_BALANCING_ENABLE_FALLBACK",
        "LOAD_BALANCING_ENABLE_COST_OPTIMIZATION",
    ]

    for env_var in env_vars:
        value = os.getenv(env_var)
        if value:
            print(f"  ✅ {env_var}: {value}")
        else:
            print(f"  ⚠️  {env_var}: 未设置 (使用默认值)")

    print("\n✅ 负载均衡配置测试完成!")


def test_strategy_validation():
    """测试策略验证"""
    print("\n🔧 测试策略验证...")

    from app.services.router import LoadBalancingStrategy

    # 测试有效策略
    valid_strategies = [
        "performance_based",
        "round_robin",
        "weighted_round_robin",
        "least_connections",
        "cost_optimized",
    ]

    for strategy in valid_strategies:
        try:
            strategy_enum = LoadBalancingStrategy(strategy)
            print(f"  ✅ 有效策略: {strategy}")
        except ValueError:
            print(f"  ❌ 无效策略: {strategy}")

    # 测试无效策略
    invalid_strategies = ["invalid_strategy", "random", ""]

    for strategy in invalid_strategies:
        try:
            strategy_enum = LoadBalancingStrategy(strategy)
            print(f"  ❌ 意外有效策略: {strategy}")
        except ValueError:
            print(f"  ✅ 正确拒绝无效策略: {strategy}")

    print("✅ 策略验证测试完成!")


if __name__ == "__main__":
    print("🚀 开始负载均衡配置测试...\n")

    test_load_balancing_config()
    test_strategy_validation()

    print("\n🎉 所有测试完成!")
