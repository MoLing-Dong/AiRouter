#!/usr/bin/env python3
"""
测试models接口性能优化效果
"""

import time
import requests
import statistics


def test_models_performance(
    base_url: str = "http://localhost:8000", iterations: int = 5
):
    """测试models接口性能"""
    print("🚀 开始测试models接口性能...")
    print(f"目标URL: {base_url}")
    print(f"测试次数: {iterations}")
    print("-" * 50)

    # 测试1: 无过滤条件的models接口
    print("📊 测试1: 无过滤条件的models接口")
    response_times = []

    for i in range(iterations):
        start_time = time.time()
        try:
            response = requests.get(f"{base_url}/v1/models/", timeout=30)
            end_time = time.time()
            response_time = end_time - start_time
            response_times.append(response_time)

            if response.status_code == 200:
                models_count = len(response.json().get("data", []))
                print(f"  第{i+1}次: {response_time:.3f}s, 返回{models_count}个模型")
            else:
                print(f"  第{i+1}次: 失败 (状态码: {response.status_code})")

        except Exception as e:
            print(f"  第{i+1}次: 异常 - {e}")

    if response_times:
        avg_time = statistics.mean(response_times)
        min_time = min(response_times)
        max_time = max(response_times)
        print(f"  平均响应时间: {avg_time:.3f}s")
        print(f"  最快响应时间: {min_time:.3f}s")
        print(f"  最慢响应时间: {max_time:.3f}s")
        print(f"  性能提升: 从6s优化到{avg_time:.3f}s (提升{(6-avg_time)/6*100:.1f}%)")

    print()

    # 测试2: 带过滤条件的models接口
    print("📊 测试2: 带过滤条件的models接口 (TEXT能力)")
    response_times_filtered = []

    for i in range(iterations):
        start_time = time.time()
        try:
            response = requests.get(
                f"{base_url}/v1/models/?capabilities=TEXT", timeout=30
            )
            end_time = time.time()
            response_time = end_time - start_time
            response_times_filtered.append(response_time)

            if response.status_code == 200:
                models_count = len(response.json().get("data", []))
                print(f"  第{i+1}次: {response_time:.3f}s, 返回{models_count}个模型")
            else:
                print(f"  第{i+1}次: 失败 (状态码: {response.status_code})")

        except Exception as e:
            print(f"  第{i+1}次: 异常 - {e}")

    if response_times_filtered:
        avg_time_filtered = statistics.mean(response_times_filtered)
        print(f"  平均响应时间: {avg_time_filtered:.3f}s")

    print()

    # 测试3: 缓存效果测试
    print("📊 测试3: 缓存效果测试 (连续请求)")
    cache_response_times = []

    for i in range(3):
        start_time = time.time()
        try:
            response = requests.get(f"{base_url}/v1/models/", timeout=30)
            end_time = time.time()
            response_time = end_time - start_time
            cache_response_times.append(response_time)

            if response.status_code == 200:
                models_count = len(response.json().get("data", []))
                cache_status = (
                    "缓存命中" if i > 0 and response_time < 0.1 else "缓存未命中"
                )
                print(
                    f"  第{i+1}次: {response_time:.3f}s, 返回{models_count}个模型 ({cache_status})"
                )
            else:
                print(f"  第{i+1}次: 失败 (状态码: {response.status_code})")

        except Exception as e:
            print(f"  第{i+1}次: 异常 - {e}")

    print()
    print("🎯 性能优化总结:")
    print(f"  • 原始性能: ~6秒")
    print(f"  • 优化后性能: ~{avg_time:.3f}秒")
    print(f"  • 性能提升: {(6-avg_time)/6*100:.1f}%")
    print(
        f"  • 缓存效果: 连续请求响应时间差异 {max(cache_response_times) - min(cache_response_times):.3f}秒"
    )

    if avg_time < 1.0:
        print("  ✅ 性能优化成功！响应时间已优化到1秒以内")
    elif avg_time < 3.0:
        print("  ⚠️  性能有所改善，但仍有优化空间")
    else:
        print("  ❌ 性能优化效果不明显，需要进一步分析")


if __name__ == "__main__":
    import sys

    base_url = "http://localhost:8000"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    test_models_performance(base_url)
