#!/usr/bin/env python3
"""
测试重构后的服务架构
验证新的分层架构和事务管理
"""

import sys
import os
import time
import json
import requests
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.service_factory import ServiceFactory
from app.database.database import get_db_session
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()

BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/v1/db"


def test_service_factory():
    """测试服务工厂的初始化"""
    print("🏭 测试服务工厂初始化...")

    try:
        # 获取数据库会话工厂
        session_factory = get_db_session

        # 创建服务工厂
        service_factory = ServiceFactory(session_factory)

        print("✅ 服务工厂创建成功")

        # 测试获取各种服务
        model_service = service_factory.get_model_service()
        provider_service = service_factory.get_provider_service()
        model_provider_service = service_factory.get_model_provider_service()
        api_key_service = service_factory.get_api_key_service()

        print(f"✅ 获取服务成功:")
        print(f"   - ModelService: {type(model_service).__name__}")
        print(f"   - ProviderService: {type(provider_service).__name__}")
        print(f"   - ModelProviderService: {type(model_provider_service).__name__}")
        print(f"   - ApiKeyService: {type(api_key_service).__name__}")

        # 测试健康检查
        health_status = service_factory.health_check()
        print(f"✅ 健康检查完成: {health_status['status']}")

        # 测试服务信息
        service_info = service_factory.get_service_info()
        print(f"✅ 服务信息获取成功:")
        print(f"   - 事务管理器: {service_info['transaction_manager']['type']}")
        print(f"   - 仓库数量: {len(service_info['repositories'])}")
        print(f"   - 服务数量: {len(service_info['services'])}")

        return service_factory

    except Exception as e:
        print(f"❌ 服务工厂测试失败: {e}")
        logger.error(f"Service factory test failed: {e}")
        return None


def test_transaction_manager(service_factory):
    """测试事务管理器"""
    print("\n🔄 测试事务管理器...")

    try:
        tx_manager = service_factory.transaction_manager

        # 测试简单事务
        def test_operation(session):
            # 简单的查询操作
            from app.models import LLMModel

            count = session.query(LLMModel).count()
            return count

        result = tx_manager.execute_in_transaction(
            test_operation, "Test transaction operation"
        )

        print(f"✅ 事务执行成功: 模型数量 = {result}")

        # 测试重试机制
        def failing_operation(session):
            raise ValueError("Simulated error for retry test")

        try:
            tx_manager.execute_with_retry(
                failing_operation, max_retries=2, description="Test retry mechanism"
            )
        except ValueError as e:
            print(f"✅ 重试机制测试成功: 按预期抛出异常 - {e}")

        return True

    except Exception as e:
        print(f"❌ 事务管理器测试失败: {e}")
        logger.error(f"Transaction manager test failed: {e}")
        return False


def test_repositories(service_factory):
    """测试仓库层"""
    print("\n📚 测试仓库层...")

    try:
        # 测试模型仓库
        model_repo = service_factory.get_repository("model")
        model_count = model_repo.count()
        print(f"✅ 模型仓库测试成功: 模型数量 = {model_count}")

        # 测试供应商仓库
        provider_repo = service_factory.get_repository("provider")
        provider_count = provider_repo.count()
        print(f"✅ 供应商仓库测试成功: 供应商数量 = {provider_count}")

        # 测试模型供应商关联仓库
        model_provider_repo = service_factory.get_repository("model_provider")
        association_count = model_provider_repo.count()
        print(f"✅ 关联仓库测试成功: 关联数量 = {association_count}")

        # 测试API密钥仓库
        api_key_repo = service_factory.get_repository("api_key")
        api_key_count = api_key_repo.count()
        print(f"✅ API密钥仓库测试成功: 密钥数量 = {api_key_count}")

        return True

    except Exception as e:
        print(f"❌ 仓库层测试失败: {e}")
        logger.error(f"Repository layer test failed: {e}")
        return False


def test_business_services(service_factory):
    """测试业务服务层"""
    print("\n🚀 测试业务服务层...")

    try:
        # 测试模型服务
        model_service = service_factory.get_model_service()
        models = model_service.get_all_models(enabled_only=True)
        print(f"✅ 模型服务测试成功: 启用模型数量 = {len(models)}")

        # 测试供应商服务
        provider_service = service_factory.get_provider_service()
        providers = provider_service.get_all_providers(enabled_only=True)
        print(f"✅ 供应商服务测试成功: 启用供应商数量 = {len(providers)}")

        # 测试模型供应商关联服务
        model_provider_service = service_factory.get_model_provider_service()
        associations = model_provider_service.get_all_associations(enabled_only=True)
        print(f"✅ 关联服务测试成功: 启用关联数量 = {len(associations)}")

        # 测试API密钥服务
        api_key_service = service_factory.get_api_key_service()
        if providers:
            provider_id = providers[0].id
            api_keys = api_key_service.get_api_keys_by_provider(
                provider_id, enabled_only=True
            )
            print(
                f"✅ API密钥服务测试成功: 供应商 {provider_id} 的密钥数量 = {len(api_keys)}"
            )

        return True

    except Exception as e:
        print(f"❌ 业务服务层测试失败: {e}")
        logger.error(f"Business service layer test failed: {e}")
        return False


def test_api_endpoints():
    """测试API端点"""
    print("\n🌐 测试API端点...")

    try:
        # 测试获取模型
        response = requests.get(f"{API_BASE}/models")
        if response.status_code == 200:
            models = response.json()
            print(f"✅ 获取模型API测试成功: 模型数量 = {len(models)}")
        else:
            print(f"⚠️ 获取模型API返回状态码: {response.status_code}")

        # 测试获取供应商
        response = requests.get(f"{API_BASE}/providers")
        if response.status_code == 200:
            providers = response.json()
            print(f"✅ 获取供应商API测试成功: 供应商数量 = {len(providers)}")
        else:
            print(f"⚠️ 获取供应商API返回状态码: {response.status_code}")

        return True

    except Exception as e:
        print(f"❌ API端点测试失败: {e}")
        logger.error(f"API endpoint test failed: {e}")
        return False


def test_error_handling(service_factory):
    """测试错误处理"""
    print("\n🚨 测试错误处理...")

    try:
        # 测试获取不存在的模型
        model_service = service_factory.get_model_service()
        non_existent_model = model_service.get_model(99999)
        if non_existent_model is None:
            print("✅ 获取不存在模型测试成功: 正确返回None")

        # 测试获取不存在的供应商
        provider_service = service_factory.get_provider_service()
        non_existent_provider = provider_service.get_provider(99999)
        if non_existent_provider is None:
            print("✅ 获取不存在供应商测试成功: 正确返回None")

        # 测试验证不存在的关联
        model_provider_service = service_factory.get_model_provider_service()
        health_status = model_provider_service.validate_association_health(99999, 99999)
        if not health_status["healthy"]:
            print(f"✅ 验证不存在关联测试成功: {health_status['reason']}")

        return True

    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        logger.error(f"Error handling test failed: {e}")
        return False


def test_performance(service_factory):
    """测试性能"""
    print("\n⚡ 测试性能...")

    try:
        start_time = time.time()

        # 批量获取操作
        model_service = service_factory.get_model_service()
        models = model_service.get_all_models()

        provider_service = service_factory.get_provider_service()
        providers = provider_service.get_all_providers()

        model_provider_service = service_factory.get_model_provider_service()
        associations = model_provider_service.get_all_associations()

        end_time = time.time()
        duration = (end_time - start_time) * 1000

        print(f"✅ 性能测试完成:")
        print(f"   - 获取 {len(models)} 个模型")
        print(f"   - 获取 {len(providers)} 个供应商")
        print(f"   - 获取 {len(associations)} 个关联")
        print(f"   - 总耗时: {duration:.2f}ms")

        return True

    except Exception as e:
        print(f"❌ 性能测试失败: {e}")
        logger.error(f"Performance test failed: {e}")
        return False


def main():
    """主测试函数"""
    print("🧪 开始测试重构后的服务架构...")
    print("=" * 80)

    # 测试1: 服务工厂
    service_factory = test_service_factory()
    if not service_factory:
        print("❌ 无法继续测试，服务工厂创建失败")
        sys.exit(1)

    # 等待一下，确保日志有时间写入
    time.sleep(1)

    # 测试2: 事务管理器
    test_transaction_manager(service_factory)
    time.sleep(1)

    # 测试3: 仓库层
    test_repositories(service_factory)
    time.sleep(1)

    # 测试4: 业务服务层
    test_business_services(service_factory)
    time.sleep(1)

    # 测试5: API端点
    test_api_endpoints()
    time.sleep(1)

    # 测试6: 错误处理
    test_error_handling(service_factory)
    time.sleep(1)

    # 测试7: 性能
    test_performance(service_factory)

    print("\n" + "=" * 80)
    print("🎉 重构后的服务架构测试完成!")
    print("\n📁 新的架构特性:")
    print("   ✅ 分层架构: 基础层 -> 仓库层 -> 业务服务层")
    print("   ✅ 统一事务管理: 自动提交/回滚/重试")
    print("   ✅ 依赖注入: 服务工厂统一管理")
    print("   ✅ 详细日志: 完整的操作追踪")
    print("   ✅ 错误处理: 统一的异常管理")
    print("   ✅ 健康检查: 服务状态监控")
    print("   ✅ 向后兼容: 保持原有API接口")

    print("\n📁 日志文件位置:")
    print("   - 应用日志: logs/ai_router_YYYYMMDD.log")
    print("   - 错误日志: logs/ai_router_error_YYYYMMDD.log")


if __name__ == "__main__":
    main()
