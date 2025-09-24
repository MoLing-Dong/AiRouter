#!/usr/bin/env python3
"""
实时流式响应测试
测试零延迟管道是否工作
"""

import asyncio
import httpx
import json
import time
import os
import threading


class RealtimeStreamTest:
    def __init__(self):
        self.chunks_received = 0
        self.start_time = None
        self.first_chunk_time = None

    async def test_realtime_pipeline(self):
        """测试实时流式管道"""

        api_key = os.getenv("API_KEY")
        if not api_key:
            print("❌ 需要设置 API_KEY 环境变量")
            return

        print("🚀 实时流式管道测试")
        print("=" * 50)
        print(f"🔑 API密钥: {api_key[:8]}***")
        print()

        url = "http://localhost:8000/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": "请写一首关于人工智能的诗，要求每个字都有深意，大约200字",
                }
            ],
            "stream": True,
            "temperature": 0.8,
            "max_tokens": 400,
        }

        print("🌊 发起实时流式请求...")
        print("📡 建立连接...")

        self.start_time = time.time()

        try:
            # 使用更激进的超时设置
            timeout = httpx.Timeout(
                connect=5.0,  # 连接超时
                read=1.0,  # 读取超时（更短以检测延迟）
                write=5.0,  # 写入超时
                pool=60.0,  # 连接池超时
            )

            async with httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(max_connections=1),
                http2=False,  # 强制HTTP/1.1
            ) as client:

                async with client.stream(
                    "POST", url, json=data, headers=headers
                ) as response:

                    print(f"📊 响应状态: {response.status_code}")
                    print(f"📊 响应头: Connection={response.headers.get('connection')}")
                    print(f"📊 传输编码: {response.headers.get('transfer-encoding')}")
                    print()

                    if response.status_code != 200:
                        print(f"❌ 请求失败: {response.status_code}")
                        return

                    print("🔥 实时管道已建立，开始接收...")
                    print("💬 内容输出: ", end="", flush=True)

                    # 监控线程，检测延迟
                    stop_monitoring = False

                    def monitor_delay():
                        last_chunk_time = time.time()
                        while not stop_monitoring:
                            time.sleep(0.1)  # 每100ms检查一次
                            current_time = time.time()
                            if (
                                current_time - last_chunk_time > 2.0
                            ):  # 超过2秒没有新chunk
                                print(
                                    f"\n⚠️  检测到延迟: {current_time - last_chunk_time:.1f}秒无新数据"
                                )
                                last_chunk_time = current_time

                    # 启动监控线程
                    monitor_thread = threading.Thread(target=monitor_delay, daemon=True)
                    monitor_thread.start()

                    try:
                        async for line in response.aiter_lines():
                            if line.strip():
                                current_time = time.time()
                                self.chunks_received += 1

                                # 记录首个chunk时间
                                if self.first_chunk_time is None:
                                    self.first_chunk_time = current_time
                                    delay = self.first_chunk_time - self.start_time
                                    print(f"\n⚡ 首个chunk到达! 延迟: {delay:.3f}秒")
                                    print("💬 内容输出: ", end="", flush=True)

                                # 处理SSE数据
                                if line.startswith("data: "):
                                    data_part = line[6:]

                                    if data_part.strip() == "[DONE]":
                                        print("\n✅ 流式传输完成")
                                        break

                                    try:
                                        chunk_data = json.loads(data_part)

                                        # 跳过开始信号
                                        if chunk_data.get("type") == "stream_start":
                                            print(f"\n🎬 管道启动信号")
                                            print("💬 内容输出: ", end="", flush=True)
                                            continue

                                        # 提取并实时显示内容
                                        if (
                                            "choices" in chunk_data
                                            and chunk_data["choices"]
                                        ):
                                            choice = chunk_data["choices"][0]
                                            if (
                                                "delta" in choice
                                                and "content" in choice["delta"]
                                            ):
                                                content = choice["delta"]["content"]
                                                if content:
                                                    # 实时输出，无缓冲
                                                    print(content, end="", flush=True)

                                        # 每50个chunk显示一次统计
                                        if self.chunks_received % 50 == 0:
                                            elapsed = current_time - self.start_time
                                            rate = self.chunks_received / elapsed
                                            print(
                                                f"\n[{elapsed:.1f}s] {self.chunks_received} chunks, {rate:.1f} chunks/s"
                                            )
                                            print("💬 内容输出: ", end="", flush=True)

                                    except json.JSONDecodeError:
                                        pass  # 忽略格式错误

                    finally:
                        stop_monitoring = True

                    total_time = time.time() - self.start_time

                    print(f"\n\n📊 实时管道性能统计:")
                    print(f"   • 总耗时: {total_time:.3f}秒")
                    print(
                        f"   • 首chunk延迟: {(self.first_chunk_time - self.start_time):.3f}秒"
                    )
                    print(f"   • 总chunk数: {self.chunks_received}")
                    print(
                        f"   • 平均传输率: {self.chunks_received/total_time:.1f} chunks/秒"
                    )
                    print(
                        f"   • 平均chunk间隔: {total_time/self.chunks_received*1000:.1f}毫秒"
                    )

                    # 性能判断
                    first_chunk_delay = self.first_chunk_time - self.start_time
                    avg_interval = total_time / self.chunks_received * 1000

                    print(f"\n🎯 实时性能评估:")
                    if first_chunk_delay < 1.0:
                        print("   ✅ 首chunk延迟优秀 (< 1秒)")
                    elif first_chunk_delay < 3.0:
                        print("   ⚠️  首chunk延迟一般 (1-3秒)")
                    else:
                        print("   ❌ 首chunk延迟过高 (> 3秒)")

                    if avg_interval < 50:
                        print("   ✅ chunk间隔优秀 (< 50ms)")
                    elif avg_interval < 100:
                        print("   ⚠️  chunk间隔一般 (50-100ms)")
                    else:
                        print("   ❌ chunk间隔过高 (> 100ms)")

                    if self.chunks_received > 50:
                        print("   ✅ chunk数量充足，流式体验流畅")
                    else:
                        print("   ⚠️  chunk数量较少，可能存在缓冲")

        except Exception as e:
            print(f"\n❌ 测试失败: {e}")

    async def test_comparison(self):
        """对比测试：流式 vs 非流式"""
        print("\n" + "=" * 50)
        print("🔄 对比测试：非流式响应")

        api_key = os.getenv("API_KEY")
        url = "http://localhost:8000/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {
                    "role": "user",
                    "content": "请写一首关于人工智能的诗，要求每个字都有深意，大约200字",
                }
            ],
            "stream": False,
            "temperature": 0.8,
            "max_tokens": 400,
        }

        start_time = time.time()

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(url, json=data, headers=headers)

                total_time = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    content = result["choices"][0]["message"]["content"]

                    print(f"📊 非流式响应:")
                    print(f"   • 总耗时: {total_time:.3f}秒")
                    print(f"   • 内容长度: {len(content)}字符")
                    print(f"   • 用户体验: 等待{total_time:.1f}秒后一次性看到结果")

                    print(f"\n💡 对比分析:")
                    if hasattr(self, "first_chunk_time") and self.first_chunk_time:
                        first_delay = self.first_chunk_time - self.start_time
                        print(f"   • 流式首字延迟: {first_delay:.1f}秒")
                        print(f"   • 非流式总延迟: {total_time:.1f}秒")
                        print(
                            f"   • 流式优势: 用户提前{total_time - first_delay:.1f}秒看到内容"
                        )
                else:
                    print(f"❌ 非流式请求失败: {response.status_code}")

        except Exception as e:
            print(f"❌ 对比测试失败: {e}")


async def main():
    """主测试函数"""
    tester = RealtimeStreamTest()
    await tester.test_realtime_pipeline()
    await tester.test_comparison()

    print(f"\n🎯 优化建议:")
    print(f"   • 确保服务使用单worker模式")
    print(f"   • 检查网络环境，避免代理缓冲")
    print(f"   • 监控服务日志查看管道状态")
    print(f"   • 实时管道的目标是让用户立即看到内容生成")


if __name__ == "__main__":
    print("🔧 实时流式管道测试工具")
    print("使用方法:")
    print("  1. export API_KEY=your-volcengine-api-key")
    print("  2. python run.py  # 启动服务")
    print("  3. python realtime_test.py  # 运行测试")
    print()

    asyncio.run(main())
