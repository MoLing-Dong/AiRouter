# 适配器池 (Adapter Pool)

## 概述

适配器池是一个用于管理和重用适配器实例的系统，旨在提高性能并减少资源开销。通过池化适配器，系统可以：

- 减少适配器创建和销毁的开销
- 复用HTTP连接
- 提供更好的并发处理能力
- 自动管理适配器的生命周期

## 主要特性

### 1. 自动池管理

- **最小池大小**: 每个模型-提供商组合维护最少2个适配器实例
- **最大池大小**: 每个模型-提供商组合最多10个适配器实例
- **自动扩展**: 当池中适配器不足时自动创建新实例
- **自动清理**: 定期清理过期和不可用的适配器

### 2. 健康检查

- **定期检查**: 每5分钟对所有可用适配器进行健康检查
- **状态管理**: 自动标记不健康的适配器
- **自动恢复**: 当适配器恢复健康时自动重新启用

### 3. 生命周期管理

- **使用计数**: 跟踪每个适配器的使用次数
- **空闲时间**: 监控适配器的最后使用时间
- **自动过期**: 超过最大使用次数或空闲时间的适配器会被自动清理

### 4. 并发安全

- **线程安全**: 使用异步锁确保并发访问安全
- **等待机制**: 当池满时，请求会等待可用的适配器
- **超时处理**: 设置最大等待时间避免无限等待

## 配置参数

```python
class AdapterPool:
    def __init__(self):
        self.max_pool_size: int = 10      # 每个池的最大大小
        self.min_pool_size: int = 2       # 每个池的最小大小
        self.cleanup_interval: float = 60.0        # 清理间隔（秒）
        self.health_check_interval: float = 300.0  # 健康检查间隔（秒）
```

## 使用方法

### 1. 基本使用

```python
from app.services.adapter_pool import adapter_pool

# 获取适配器
adapter = await adapter_pool.get_adapter("model_name", "provider_name")

# 使用适配器
response = await adapter.chat_completion(request)

# 释放适配器
await adapter_pool.release_adapter(adapter, "model_name", "provider_name")
```

### 2. 使用上下文管理器（推荐）

```python
from app.services.adapter_pool import adapter_pool

# 使用上下文管理器自动管理适配器生命周期
async with adapter_pool.get_adapter_context("model_name", "provider_name") as adapter:
    if adapter:
        response = await adapter.chat_completion(request)
    # 适配器会在退出上下文时自动释放
```

### 3. 在负载均衡中使用

适配器池已经集成到负载均衡策略管理器中，会自动处理适配器的获取和释放：

```python
# 在负载均衡策略中，适配器会自动从池中获取和释放
response = await strategy_manager.execute_strategy(request, model_providers, strategy, config)
```

## API 端点

### 1. 获取池统计信息

```
GET /v1/pool/stats
```

响应示例：

```json
{
    "success": true,
    "data": {
        "total_pools": 2,
        "pools": {
            "doubao-seed-1-6-flash-250715:Volcengine": {
                "total": 5,
                "available": 3,
                "in_use": 2,
                "unhealthy": 0,
                "expired": 0,
                "max_pool_size": 10,
                "min_pool_size": 2
            }
        }
    },
    "message": "获取适配器池统计信息成功"
}
```

### 2. 获取池状态

```
GET /v1/pool/status
```

响应示例：

```json
{
    "success": true,
    "data": {
        "total_pools": 2,
        "total_adapters": 10,
        "available_adapters": 6,
        "in_use_adapters": 4,
        "unhealthy_adapters": 0,
        "utilization_rate": 40.0,
        "health_rate": 100.0
    },
    "message": "获取适配器池状态成功"
}
```

### 3. 手动清理池

```
POST /v1/pool/cleanup
```

### 4. 手动健康检查

```
POST /v1/pool/health-check
```

## 监控和调试

### 1. 日志输出

适配器池会输出详细的日志信息：

```
🔄 启动适配器池...
🔧 初始化适配器池: doubao-seed-1-6-flash-250715:Volcengine
✅ 创建适配器成功: doubao-seed-1-6-flash-250715:Volcengine
🔄 从池中获取适配器: doubao-seed-1-6-flash-250715:Volcengine (使用次数: 1)
🔄 释放适配器回池: doubao-seed-1-6-flash-250715:Volcengine (使用次数: 1)
🧹 清理了 2 个过期适配器
```

### 2. 性能指标

- **利用率**: 当前使用中的适配器占总适配器的百分比
- **健康率**: 健康适配器占总适配器的百分比
- **平均响应时间**: 每个适配器的平均响应时间
- **成功率**: 每个适配器的请求成功率

## 最佳实践

### 1. 合理配置池大小

- 根据并发需求调整 `max_pool_size`
- 根据响应时间要求调整 `min_pool_size`
- 监控池利用率，避免资源浪费

### 2. 定期监控

- 定期检查池统计信息
- 监控适配器健康状态
- 关注错误率和响应时间

### 3. 错误处理

- 适配器池会自动处理适配器创建失败的情况
- 不健康的适配器会被自动标记和清理
- 系统会自动尝试恢复健康的适配器

### 4. 资源管理

- 使用上下文管理器确保适配器正确释放
- 避免长时间持有适配器
- 定期清理过期的适配器

## 故障排除

### 1. 适配器获取失败

- 检查模型和提供商配置是否正确
- 确认API密钥是否有效
- 查看健康检查状态

### 2. 池满等待

- 增加 `max_pool_size` 配置
- 检查是否有适配器没有正确释放
- 监控池利用率

### 3. 性能问题

- 检查适配器响应时间
- 监控池大小是否合适
- 查看健康检查频率

## 测试

运行测试脚本验证适配器池功能：

```bash
python test_adapter_pool.py
```

测试包括：

- 基本适配器获取和释放
- 上下文管理器使用
- 并发获取测试
- 健康检查测试
- 清理功能测试
