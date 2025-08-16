#!/usr/bin/env python3
"""
测试重构后的服务是否正常工作
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_service_manager():
    """测试服务管理器"""
    print("🧪 测试服务管理器...")

    try:
        from app.services.service_manager import service_manager

        # 测试获取服务
        db_service = service_manager.get_database_service()
        model_service = service_manager.get_model_service()
        provider_service = service_manager.get_provider_service()
        model_provider_service = service_manager.get_model_provider_service()
        health_check_service = service_manager.get_health_check_service()

        print("✅ 所有服务实例创建成功")

        # 测试服务信息
        service_info = service_manager.get_service_info()
        print(f"📊 服务信息: {service_info}")

        # 测试健康检查
        health_status = service_manager.health_check()
        print(f"🏥 服务健康状态: {health_status}")

        return True

    except Exception as e:
        print(f"❌ 服务管理器测试失败: {e}")
        return False


def test_database_service():
    """测试数据库服务"""
    print("🧪 测试数据库服务...")

    try:
        from app.services.database_service import db_service

        # 测试数据库连接
        with db_service.get_session() as session:
            result = session.execute("SELECT 1").scalar()
            assert result == 1
            print("✅ 数据库连接测试成功")

        # 测试获取模型
        models = db_service.get_all_models()
        print(f"✅ 获取模型成功，共 {len(models)} 个模型")

        # 测试获取提供商
        providers = db_service.get_all_providers()
        print(f"✅ 获取提供商成功，共 {len(providers)} 个提供商")

        return True

    except Exception as e:
        print(f"❌ 数据库服务测试失败: {e}")
        return False


def test_model_service():
    """测试模型服务"""
    print("🧪 测试模型服务...")

    try:
        from app.services.service_manager import get_model_service

        model_service = get_model_service()

        # 测试获取所有模型
        models = model_service.get_all_models()
        print(f"✅ 模型服务获取模型成功，共 {len(models)} 个模型")

        # 测试批量获取能力
        if models:
            model_ids = [models[0].id]
            capabilities = model_service.get_all_models_capabilities_batch(model_ids)
            print(f"✅ 批量获取模型能力成功: {capabilities}")

        return True

    except Exception as e:
        print(f"❌ 模型服务测试失败: {e}")
        return False


def test_provider_service():
    """测试提供商服务"""
    print("🧪 测试提供商服务...")

    try:
        from app.services.service_manager import get_provider_service

        provider_service = get_provider_service()

        # 测试获取所有提供商
        providers = provider_service.get_all_providers()
        print(f"✅ 提供商服务获取提供商成功，共 {len(providers)} 个提供商")

        return True

    except Exception as e:
        print(f"❌ 提供商服务测试失败: {e}")
        return False


def test_model_provider_service():
    """测试模型提供商服务"""
    print("🧪 测试模型提供商服务...")

    try:
        from app.services.service_manager import get_model_provider_service

        model_provider_service = get_model_provider_service()

        # 测试获取可用策略
        strategies = model_provider_service.get_available_strategies()
        print(f"✅ 获取可用策略成功: {strategies}")

        return True

    except Exception as e:
        print(f"❌ 模型提供商服务测试失败: {e}")
        return False


def test_health_check_service():
    """测试健康检查服务"""
    print("🧪 测试健康检查服务...")

    try:
        from app.services.service_manager import get_health_check_service

        health_check_service = get_health_check_service()

        # 测试健康状态映射
        healthy_status = health_check_service._map_health_status("healthy")
        unhealthy_status = health_check_service._map_health_status("unhealthy")
        degraded_status = health_check_service._map_health_status("degraded")

        print(f"✅ 健康状态映射测试成功:")
        print(f"   healthy -> {healthy_status}")
        print(f"   unhealthy -> {unhealthy_status}")
        print(f"   degraded -> {degraded_status}")

        return True

    except Exception as e:
        print(f"❌ 健康检查服务测试失败: {e}")
        return False


def main():
    """主测试函数"""
    print("🚀 开始测试重构后的服务...")
    print("=" * 50)

    tests = [
        test_service_manager,
        test_database_service,
        test_model_service,
        test_provider_service,
        test_model_provider_service,
        test_health_check_service,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ 测试 {test.__name__} 异常: {e}")
            print()

    print("=" * 50)
    print(f"📊 测试结果: {passed}/{total} 通过")

    if passed == total:
        print("🎉 所有测试通过！重构成功！")
        return 0
    else:
        print("⚠️ 部分测试失败，需要检查")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
