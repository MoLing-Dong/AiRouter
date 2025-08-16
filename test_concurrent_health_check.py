#!/usr/bin/env python3
"""
测试并发健康检查性能的脚本
"""

import sys
import os
import time
import asyncio
from typing import Dict, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


async def test_sequential_health_check():
    """测试串行健康检查性能"""
    print("🧪 测试串行健康检查...")
    
    try:
        from app.services import adapter_manager
        
        start_time = time.time()
        result = await adapter_manager.health_check_all()
        execution_time = time.time() - start_time
        
        print(f"✅ 串行健康检查完成")
        print(f"   执行时间: {execution_time:.2f} 秒")
        print(f"   检查结果数量: {len(result)}")
        
        return execution_time, result
        
    except Exception as e:
        print(f"❌ 串行健康检查失败: {e}")
        return None, None


async def test_concurrent_health_check():
    """测试并发健康检查性能"""
    print("🧪 测试并发健康检查...")
    
    try:
        from app.services import adapter_manager
        
        start_time = time.time()
        result = await adapter_manager.health_checker.check_all_models_with_timeout(
            adapter_manager.get_available_models(),
            adapter_manager.model_adapters,
            timeout=30.0
        )
        execution_time = time.time() - start_time
        
        print(f"✅ 并发健康检查完成")
        print(f"   执行时间: {execution_time:.2f} 秒")
        print(f"   检查结果数量: {len(result)}")
        
        return execution_time, result
        
    except Exception as e:
        print(f"❌ 并发健康检查失败: {e}")
        return None, None


async def test_concurrent_vs_sequential():
    """对比并发和串行健康检查性能"""
    print("🚀 开始性能对比测试...")
    print("=" * 60)
    
    # 测试串行健康检查
    sequential_time, sequential_result = await test_sequential_health_check()
    print()
    
    # 测试并发健康检查
    concurrent_time, concurrent_result = await test_concurrent_health_check()
    print()
    
    # 性能对比
    if sequential_time and concurrent_time:
        print("📊 性能对比结果:")
        print("=" * 60)
        print(f"串行执行时间: {sequential_time:.2f} 秒")
        print(f"并发执行时间: {concurrent_time:.2f} 秒")
        
        if sequential_time > 0:
            speedup = sequential_time / concurrent_time
            improvement_percent = ((sequential_time - concurrent_time) / sequential_time) * 100
            
            print(f"性能提升倍数: {speedup:.2f}x")
            print(f"性能提升百分比: {improvement_percent:.1f}%")
            
            if speedup > 1.5:
                print("🎉 并发健康检查显著提升了性能！")
            elif speedup > 1.1:
                print("✅ 并发健康检查有一定性能提升")
            else:
                print("⚠️ 并发健康检查性能提升不明显")
        else:
            print("⚠️ 无法计算性能提升")
    else:
        print("❌ 性能对比测试失败")
    
    print("=" * 60)
    
    # 结果一致性检查
    if sequential_result and concurrent_result:
        print("🔍 结果一致性检查:")
        sequential_keys = set(sequential_result.keys())
        concurrent_keys = set(concurrent_result.keys())
        
        if sequential_keys == concurrent_keys:
            print("✅ 并发和串行检查结果完全一致")
        else:
            print("⚠️ 并发和串行检查结果不完全一致")
            print(f"   串行结果键: {len(sequential_keys)}")
            print(f"   并发结果键: {len(concurrent_keys)}")
            print(f"   差异: {sequential_keys.symmetric_difference(concurrent_keys)}")
    else:
        print("❌ 无法进行结果一致性检查")


async def test_health_check_timeout():
    """测试健康检查超时机制"""
    print("⏰ 测试健康检查超时机制...")
    
    try:
        from app.services import adapter_manager
        
        # 测试短超时
        print("   测试5秒超时...")
        start_time = time.time()
        result = await adapter_manager.health_checker.check_all_models_with_timeout(
            adapter_manager.get_available_models(),
            adapter_manager.model_adapters,
            timeout=5.0
        )
        execution_time = time.time() - start_time
        
        print(f"   执行时间: {execution_time:.2f} 秒")
        print(f"   结果数量: {len(result)}")
        
        # 测试长超时
        print("   测试30秒超时...")
        start_time = time.time()
        result = await adapter_manager.health_checker.check_all_models_with_timeout(
            adapter_manager.get_available_models(),
            adapter_manager.model_adapters,
            timeout=30.0
        )
        execution_time = time.time() - start_time
        
        print(f"   执行时间: {execution_time:.2f} 秒")
        print(f"   结果数量: {len(result)}")
        
        print("✅ 超时机制测试完成")
        
    except Exception as e:
        print(f"❌ 超时机制测试失败: {e}")


async def test_individual_model_health():
    """测试单个模型的健康检查"""
    print("🔍 测试单个模型健康检查...")
    
    try:
        from app.services import adapter_manager
        
        available_models = adapter_manager.get_available_models()
        if not available_models:
            print("⚠️ 没有可用的模型")
            return
        
        # 测试第一个模型
        model_name = available_models[0]
        print(f"   测试模型: {model_name}")
        
        # 串行检查
        start_time = time.time()
        sequential_result = await adapter_manager.health_check_model(model_name)
        sequential_time = time.time() - start_time
        
        # 并发检查
        start_time = time.time()
        concurrent_result = await adapter_manager.health_checker.check_model_health_with_timeout(
            model_name,
            adapter_manager.get_model_adapters(model_name),
            timeout=10.0
        )
        concurrent_time = time.time() - start_time
        
        print(f"   串行执行时间: {sequential_time:.2f} 秒")
        print(f"   并发执行时间: {concurrent_time:.2f} 秒")
        print(f"   串行结果: {len(sequential_result)} 个提供商")
        print(f"   并发结果: {len(concurrent_result)} 个提供商")
        
        print("✅ 单个模型健康检查测试完成")
        
    except Exception as e:
        print(f"❌ 单个模型健康检查测试失败: {e}")


async def main():
    """主测试函数"""
    print("🚀 开始并发健康检查性能测试...")
    print("=" * 60)
    
    tests = [
        test_concurrent_vs_sequential,
        test_health_check_timeout,
        test_individual_model_health,
    ]
    
    for test in tests:
        try:
            await test()
            print()
        except Exception as e:
            print(f"❌ 测试 {test.__name__} 失败: {e}")
            print()
    
    print("🎉 所有测试完成！")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"❌ 测试执行失败: {e}")
        sys.exit(1)
