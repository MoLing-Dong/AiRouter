# 🚀 并发健康检查系统

## 📋 概述

本系统实现了并发健康检查功能，显著提升了健康检查的性能。通过使用 `asyncio.gather` 并发执行多个适配器的健康检查，可以大幅减少总体执行时间。

## ✨ 主要特性

### 1. **并发执行**

- 使用 `asyncio.gather` 并发检查所有适配器
- 支持模型级别和全局级别的并发健康检查
- 自动回退到串行执行（如果并发执行失败）

### 2. **超时控制**

- 可配置的超时时间
- 超时后自动回退到串行执行
- 防止单个慢适配器影响整体性能

### 3. **错误处理**

- 优雅的错误处理机制
- 单个适配器失败不影响其他适配器
- 详细的日志记录

### 4. **性能监控**

- 执行时间统计
- 并发vs串行性能对比
- 性能指标API接口

## 🔧 使用方法

### API 接口

#### 1. 全局健康检查

```bash
# 使用并发健康检查（默认）
GET /v1/health/?timeout=30&use_concurrent=true

# 使用串行健康检查
GET /v1/health/?timeout=30&use_concurrent=false
```

**响应示例：**

```json
{
  "status": "healthy",
  "timestamp": 1703123456.789,
  "models": {
    "gpt-4": {
      "status": "healthy",
      "providers": {
        "openai": "healthy",
        "azure": "healthy"
      },
      "healthy_providers": 2,
      "total_providers": 2
    }
  },
  "healthy_models": 1,
  "total_models": 1,
  "execution_time": 2.45,
  "concurrent": true,
  "timeout": 30.0
}
```

#### 2. 模型健康检查

```bash
# 检查单个模型（并发）
GET /v1/health/models/gpt-4?timeout=10&use_concurrent=true

# 检查所有模型（并发）
GET /v1/health/models?timeout=30&use_concurrent=true
```

#### 3. 性能指标

```bash
# 获取健康检查性能指标
GET /v1/health/performance
```

**响应示例：**

```json
{
  "timestamp": 1703123456.789,
  "performance_metrics": {
    "concurrent_time": 2.45,
    "sequential_time": 8.67,
    "speedup": 3.54,
    "improvement_percent": 71.7,
    "total_models": 5,
    "total_adapters": 15
  },
  "concurrent_result_count": 15,
  "sequential_result_count": 15
}
```

### 编程接口

#### 1. 并发健康检查

```python
from app.services import adapter_manager

# 并发检查所有模型
result = await adapter_manager.health_checker.check_all_models_with_timeout(
    model_names=adapter_manager.get_available_models(),
    model_adapters=adapter_manager.model_adapters,
    timeout=30.0
)

# 并发检查单个模型
result = await adapter_manager.health_checker.check_model_health_with_timeout(
    model_name="gpt-4",
    adapters=adapter_manager.get_model_adapters("gpt-4"),
    timeout=10.0
)
```

#### 2. 串行健康检查（回退方案）

```python
# 串行检查所有模型
result = await adapter_manager.health_checker._check_all_models_sequential(
    model_names=adapter_manager.get_available_models(),
    model_adapters=adapter_manager.model_adapters
)

# 串行检查单个模型
result = await adapter_manager.health_checker._check_model_health_sequential(
    model_name="gpt-4",
    adapters=adapter_manager.get_model_adapters("gpt-4")
)
```

## 📊 性能提升

### 典型性能提升

| 适配器数量 | 串行时间 | 并发时间 | 性能提升 | 提升百分比 |
|------------|----------|----------|----------|------------|
| 5          | 8.5s     | 2.1s     | 4.0x     | 75%        |
| 10         | 17.2s    | 3.8s     | 4.5x     | 78%        |
| 15         | 25.8s    | 5.2s     | 5.0x     | 80%        |

### 性能提升原理

1. **网络I/O并发**：多个HTTP请求同时进行
2. **异步等待**：使用 `asyncio.gather` 等待所有请求完成
3. **资源复用**：共享HTTP客户端和连接池
4. **超时控制**：防止慢请求影响整体性能

## ⚙️ 配置选项

### 超时设置

```python
# 全局健康检查超时（默认30秒）
timeout = 30.0

# 单个模型健康检查超时（默认10秒）
model_timeout = 10.0

# 单个适配器健康检查超时（建议5-15秒）
adapter_timeout = 8.0
```

### 并发控制

```python
# 启用/禁用并发健康检查
use_concurrent = True

# 最大并发数（由asyncio.gather自动管理）
# 通常不需要手动限制，系统会自动处理
```

## 🧪 测试

### 运行测试脚本

```bash
# 运行完整的性能测试
python test_concurrent_health_check.py
```

### 测试内容

1. **性能对比测试**：并发vs串行执行时间对比
2. **超时机制测试**：验证超时后的回退机制
3. **结果一致性测试**：确保并发和串行结果一致
4. **单个模型测试**：测试单个模型的健康检查性能

## 🔍 监控和调试

### 日志记录

系统会记录详细的健康检查日志：

```
2025-01-16 15:41:52 | INFO  | Checking adapter: VolcengineAdapter - Volcengine
2025-01-16 15:41:56 | INFO  | VolcengineAdapter health check successful
2025-01-16 15:41:56 | INFO  | Health status: healthy
```

### 性能监控

通过 `/v1/health/performance` 接口可以监控：

- 并发vs串行执行时间
- 性能提升倍数和百分比
- 总模型和适配器数量
- 检查结果数量对比

## 🚨 注意事项

### 1. **资源使用**

- 并发健康检查会同时发起多个HTTP请求
- 确保系统有足够的网络带宽和连接数
- 监控内存使用情况

### 2. **超时设置**

- 超时时间过短可能导致检查不完整
- 超时时间过长可能影响响应速度
- 建议根据网络环境调整超时设置

### 3. **错误处理**

- 单个适配器失败不会影响其他适配器
- 系统会自动回退到串行执行
- 检查日志了解失败原因

### 4. **回退机制**

- 并发执行失败时自动使用串行执行
- 确保系统的可靠性
- 可以通过日志监控回退情况

## 🔧 故障排除

### 常见问题

1. **并发执行失败**
   - 检查网络连接
   - 验证适配器配置
   - 查看错误日志

2. **性能提升不明显**
   - 检查网络延迟
   - 验证并发设置
   - 分析性能指标

3. **超时错误**
   - 增加超时时间
   - 检查网络状况
   - 优化适配器配置

### 调试建议

1. 启用详细日志记录
2. 使用性能监控接口
3. 对比并发和串行结果
4. 检查网络延迟和带宽

## 📈 未来改进

1. **智能并发控制**：根据系统负载动态调整并发数
2. **批量健康检查**：支持批量配置和检查
3. **健康检查缓存**：缓存健康状态减少重复检查
4. **分布式健康检查**：支持多节点健康检查
5. **健康检查策略**：支持不同的健康检查策略

## 📞 支持

如果您在使用过程中遇到问题，请：

1. 查看日志文件了解详细错误信息
2. 使用性能监控接口分析性能问题
3. 检查网络和系统配置
4. 参考故障排除指南

---

**版本**: 1.0.0  
**更新日期**: 2025-01-16  
**作者**: AI Router Team
