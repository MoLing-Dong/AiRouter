# 数据库服务重构说明

## 重构概述

原来的 `DatabaseService` 类过于庞大（1496行），包含了太多职责，违反了单一职责原则。本次重构将其拆分为多个专门的服务类，并修复了健康检查同步问题。

## 新的服务架构

### 1. 核心服务

#### `DatabaseService` (核心数据库服务)

- **职责**: 数据库连接管理、基础CRUD操作、健康状态和指标更新
- **功能**:
  - 数据库连接和会话管理
  - 核心模型、提供商、关联表的CRUD操作
  - 健康状态和性能指标更新
  - 分数重新计算

#### `ModelService` (模型管理服务)

- **职责**: 模型相关的所有操作
- **功能**:
  - 模型CRUD操作
  - 模型配置管理
  - 模型能力管理
  - 批量查询优化

#### `ProviderService` (提供商管理服务)

- **职责**: 提供商相关的所有操作
- **功能**:
  - 提供商CRUD操作
  - API密钥管理
  - 提供商健康状态监控
  - 性能统计和推荐

#### `ModelProviderService` (模型-提供商关联服务)

- **职责**: 模型和提供商之间的关联管理
- **功能**:
  - 关联关系CRUD操作
  - 负载均衡策略管理
  - 断路器配置
  - 批量查询优化

#### `HealthCheckService` (健康检查服务)

- **职责**: 健康状态同步和监控
- **功能**:
  - 适配器健康状态同步到数据库
  - 指标数据同步
  - 失败计数管理
  - 健康状态摘要

### 2. 服务管理器

#### `ServiceManager`

- **职责**: 统一管理所有服务实例
- **功能**:
  - 服务初始化和协调
  - 服务健康检查
  - 向后兼容性支持

## 健康检查同步修复

### 问题描述

原来的健康检查机制存在以下问题：

1. 适配器的健康状态只更新了内存中的metrics，没有同步到数据库
2. 数据库中的 `llm_model_providers.last_health_check` 字段没有及时更新
3. 健康状态变化时缺乏数据库同步机制

### 解决方案

#### 1. 自动指标同步

在 `BaseAdapter.update_metrics()` 方法中添加了自动同步逻辑：

```python
def update_metrics(self, response_time: float, success: bool, tokens_used: int = 0):
    # ... 原有逻辑 ...
    
    # 自动同步到数据库
    if hasattr(self, 'model_id') and hasattr(self, 'provider_id') and self.model_id and self.provider_id:
        try:
            from app.services.health_check_service import HealthCheckService
            from app.services.database_service import db_service
            
            health_service = HealthCheckService(db_service)
            health_service.sync_adapter_metrics_to_database(
                model_id=self.model_id,
                provider_id=self.provider_id,
                response_time=response_time,
                success=success,
                tokens_used=tokens_used,
                cost=self.get_cost_estimate(tokens_used) if tokens_used > 0 else 0.0
            )
        except Exception as e:
            # 记录错误但不阻塞主操作
            logging.getLogger(__name__).warning(f"Failed to sync metrics to database: {e}")
```

#### 2. 健康状态同步

在 `BaseAdapter` 中添加了健康状态同步方法：

```python
def sync_health_status_to_database(self, health_status: str, error_message: str = None):
    """同步健康状态到数据库"""
    if not hasattr(self, 'model_id') or not hasattr(self, 'provider_id') or not self.model_id or not self.provider_id:
        return False
        
    try:
        from app.services.health_check_service import HealthCheckService
        from app.services.database_service import db_service
        
        health_service = HealthCheckService(db_service)
        return health_service.sync_adapter_health_to_database(
            model_id=self.model_id,
            provider_id=self.provider_id,
            health_status=health_status,
            response_time=self.metrics.response_time,
            success=self.metrics.success_rate > 0.5,
            error_message=error_message
        )
    except Exception as e:
        logging.getLogger(__name__).warning(f"Failed to sync health status to database: {e}")
        return False
```

#### 3. 适配器集成

所有适配器在健康状态变化时都会自动同步到数据库：

```python
# OpenAI适配器示例
except Exception as e:
    response_time = time.time() - start_time
    self.update_metrics(response_time, False)
    self.health_status = HealthStatus.UNHEALTHY
    
    # 同步健康状态到数据库
    self.sync_health_status_to_database("unhealthy", str(e))
    
    raise Exception(f"OpenAI adapter error: {str(e)}")
```

## 使用方式

### 1. 通过服务管理器

```python
from app.services.service_manager import service_manager

# 获取模型服务
model_service = service_manager.get_model_service()
models = model_service.get_all_models()

# 获取健康检查服务
health_service = service_manager.get_health_check_service()
health_status = health_service.get_health_summary(model_id, provider_id)
```

### 2. 通过便捷函数（向后兼容）

```python
from app.services.service_manager import get_model_service, get_health_check_service

model_service = get_model_service()
health_service = get_health_check_service()
```

### 3. 直接使用服务

```python
from app.services.model_service import ModelService
from app.services.database_service import db_service

model_service = ModelService(db_service)
models = model_service.get_all_models()
```

## 重构优势

1. **单一职责**: 每个服务类都有明确的职责范围
2. **可维护性**: 代码结构更清晰，易于理解和修改
3. **可扩展性**: 新增功能时只需要修改相应的服务类
4. **可测试性**: 每个服务可以独立进行单元测试
5. **健康检查同步**: 解决了健康状态不同步的问题
6. **向后兼容**: 保持了原有API的兼容性

## 注意事项

1. **循环导入**: 避免服务之间的循环导入
2. **异常处理**: 健康检查同步失败不应影响主要业务逻辑
3. **性能考虑**: 数据库同步操作在后台进行，不阻塞主流程
4. **日志记录**: 所有同步操作都有详细的日志记录

## 迁移指南

### 原有代码

```python
from app.services.database_service import db_service

# 获取模型
models = db_service.get_all_models()
```

### 新代码

```python
from app.services.service_manager import get_model_service

model_service = get_model_service()
models = model_service.get_all_models()
```

或者继续使用原有方式（向后兼容）：

```python
from app.services.database_service import db_service

# 仍然可以工作
models = db_service.get_all_models()
```
