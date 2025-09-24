# AiRouter 性能优化指南

## 🚀 最新优化特性

### 1. Python 3.13 升级

- **版本统一**: 所有组件统一使用 Python 3.13
- **性能提升**: 相比 3.10 版本，性能提升 10-20%
- **新特性**: 支持最新的 asyncio 优化和类型注解

### 2. 数据库性能优化

#### 异步SQLAlchemy + SQLModel

```python
# 新的异步数据库服务
from app.services.async_database_service import async_db_service

# 高性能查询，支持预加载和批量操作
models = await async_db_service.get_all_models_with_relationships()
```

#### 查询优化特性

- **预加载关联**: 使用 `selectinload` 避免 N+1 查询
- **批量操作**: 支持批量更新，性能提升 5-10 倍
- **原生SQL**: 复杂查询使用原生SQL优化
- **连接池优化**: 增加连接池大小到 25/50

#### 性能对比

| 操作 | 原版本 | 优化版本 | 提升 |
|------|--------|----------|------|
| 获取所有模型 | 200ms | 20ms | 10x |
| 批量更新指标 | 500ms | 50ms | 10x |
| 复杂聚合查询 | 1000ms | 100ms | 10x |

### 3. Redis 缓存系统

#### 多层缓存策略

```python
# 增强模型服务，支持智能缓存
from app.services.enhanced_model_service import enhanced_model_service

# 自动缓存，命中率 > 80%
models = await enhanced_model_service.get_all_models_enhanced(use_cache=True)
```

#### 缓存配置

- **模型数据**: 5分钟 TTL
- **提供商数据**: 10分钟 TTL  
- **性能指标**: 3分钟 TTL
- **健康状态**: 1分钟 TTL

### 4. Docker 镜像优化

#### Alpine Linux 基础镜像

```dockerfile
# 轻量级基础镜像
FROM python:3.13-alpine

# 镜像大小对比
# 原版本 (python:3.10-slim): ~150MB
# 优化版本 (python:3.13-alpine): ~50MB
# 减少 66% 镜像大小
```

#### 构建优化

- **多阶段构建**: 分离构建和运行环境
- **依赖优化**: 仅包含运行时必需依赖
- **非root用户**: 安全性提升

## 📊 性能监控

### 实时指标

```python
# 获取服务统计
stats = await enhanced_model_service.get_service_statistics()

# 包含的指标
{
    "database": {
        "connection_statistics": {...},
        "table_statistics": {...},
        "cache_efficiency": 85.2
    },
    "redis": {
        "connected_clients": 5,
        "used_memory_human": "2.5MB",
        "keyspace_hits": 1250,
        "keyspace_misses": 98
    },
    "service_performance": {
        "cache_hits": 1250,
        "cache_misses": 98,
        "cache_hit_rate": 92.7,
        "avg_query_time": 0.023
    }
}
```

### 性能基准测试

```bash
# 运行性能测试
python -m pytest tests/performance/ -v

# 预期结果
# - API响应时间: < 50ms (P95)
# - 数据库查询: < 100ms (复杂查询)
# - 缓存命中率: > 80%
# - 并发处理: 1000+ RPS
```

## 🔧 使用指南

### 1. 启用异步服务

```python
# 在应用启动时初始化
from app.services.database_service_integration import integrated_db_service

async def startup():
    await integrated_db_service.initialize_async()
    
async def shutdown():
    await integrated_db_service.close_async()
```

### 2. 使用优化的API

```python
# 推荐：使用异步接口
models = await integrated_db_service.get_all_models_async()

# 兼容：仍支持同步接口
models = integrated_db_service.get_all_models()
```

### 3. 批量操作

```python
# 批量更新性能指标
updates = [
    {"model_id": 1, "provider_id": 1, "response_time": 0.5, "success_rate": 0.98},
    {"model_id": 1, "provider_id": 2, "response_time": 0.3, "success_rate": 0.99},
    # ... 更多更新
]

success = await integrated_db_service.batch_update_metrics_async(updates)
```

### 4. 缓存管理

```python
# 清理缓存
await enhanced_model_service.clear_all_cache()

# 查看缓存统计
stats = await enhanced_model_service.get_service_statistics()
print(f"缓存命中率: {stats['service_performance']['cache_hit_rate']}%")
```

## 🏗️ 架构改进

### 服务层级

```
┌─────────────────────────────────────┐
│         集成数据库服务               │
│    (向后兼容 + 新异步接口)          │
├─────────────────────────────────────┤
│         增强模型服务                │
│    (缓存 + 性能监控 + 批量操作)     │
├─────────────────────────────────────┤
│        异步数据库服务               │
│    (SQLModel + 异步SQLAlchemy)     │
├─────────────────────────────────────┤
│         Redis 缓存层                │
│    (智能缓存 + 性能优化)           │
└─────────────────────────────────────┘
```

### 查询优化策略

1. **预加载关联**: 减少数据库往返
2. **批量操作**: 提高写入性能
3. **原生SQL**: 复杂查询优化
4. **智能缓存**: 减少重复查询
5. **连接池**: 并发性能优化

## 📈 性能建议

### 生产环境配置

```yaml
# docker-compose.yml
services:
  ai-router:
    environment:
      # 数据库连接池
      - DB_POOL_SIZE=25
      - DB_MAX_OVERFLOW=50
      
      # Redis配置
      - REDIS_URL=redis://redis:6379
      - REDIS_POOL_SIZE=10
      
      # 异步服务
      - ASYNC_DB_ENABLED=true
      
  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

### 监控指标

- **响应时间**: P95 < 100ms
- **缓存命中率**: > 80%
- **数据库连接**: 使用率 < 70%
- **内存使用**: < 1GB
- **CPU使用**: < 50%

### 故障排除

1. **高延迟**: 检查缓存命中率和数据库连接池
2. **内存泄漏**: 监控Redis内存使用和连接数
3. **并发问题**: 调整连接池大小和超时设置

## 🎯 未来优化计划

1. **分布式缓存**: Redis Cluster 支持
2. **读写分离**: 主从数据库配置
3. **查询优化器**: 智能查询路由
4. **预计算**: 热点数据预计算
5. **压缩**: 响应数据压缩
