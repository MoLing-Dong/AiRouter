# 服务架构重构文档

## 概述

本项目已完成了全面的服务架构重构，采用了分层架构设计，统一了事务管理，并提供了更好的可维护性和可扩展性。

## 架构层次

### 1. 基础层 (Base Layer)

#### 1.1 事务管理器 (Transaction Manager)

- **位置**: `app/services/base/transaction_manager.py`
- **职责**: 提供统一的事务管理接口
- **特性**:
  - 自动事务管理 (提交/回滚/关闭)
  - 重试机制 (指数退避)
  - 详细日志记录
  - 性能监控

#### 1.2 基础仓库 (Base Repository)

- **位置**: `app/services/base/repository_base.py`
- **职责**: 提供通用的数据访问模式
- **特性**:
  - CRUD 操作抽象
  - 数据验证接口
  - 事务集成
  - 类型安全

### 2. 仓库层 (Repository Layer)

#### 2.1 模型仓库 (Model Repository)

- **位置**: `app/services/repositories/model_repository.py`
- **职责**: 模型相关的数据访问
- **功能**:
  - 模型 CRUD 操作
  - 模型搜索和统计
  - 模型与供应商关联查询

#### 2.2 供应商仓库 (Provider Repository)

- **位置**: `app/services/repositories/provider_repository.py`
- **职责**: 供应商相关的数据访问
- **功能**:
  - 供应商 CRUD 操作
  - 供应商搜索和统计
  - 供应商端点管理

#### 2.3 模型供应商关联仓库 (Model-Provider Repository)

- **位置**: `app/services/repositories/model_provider_repository.py`
- **职责**: 模型供应商关联的数据访问
- **功能**:
  - 关联 CRUD 操作
  - 权重和优先级管理
  - 关联健康检查

#### 2.4 API密钥仓库 (API Key Repository)

- **位置**: `app/services/repositories/api_key_repository.py`
- **职责**: API密钥相关的数据访问
- **功能**:
  - 密钥 CRUD 操作
  - 配额管理
  - 密钥轮换

### 3. 业务服务层 (Business Service Layer)

#### 3.1 模型服务 (Model Service)

- **位置**: `app/services/business/model_service.py`
- **职责**: 模型相关的业务逻辑
- **功能**:
  - 模型创建与供应商关联
  - 模型生命周期管理
  - 业务规则验证

#### 3.2 供应商服务 (Provider Service)

- **位置**: `app/services/business/provider_service.py`
- **职责**: 供应商相关的业务逻辑
- **功能**:
  - 供应商管理
  - 可用性验证
  - 关联关系管理

#### 3.3 模型供应商关联服务 (Model-Provider Service)

- **位置**: `app/services/business/model_provider_service.py`
- **职责**: 关联关系的业务逻辑
- **功能**:
  - 关联创建和管理
  - 权重和优先级调整
  - 关联健康监控

#### 3.4 API密钥服务 (API Key Service)

- **位置**: `app/services/business/api_key_service.py`
- **职责**: API密钥的业务逻辑
- **功能**:
  - 密钥管理
  - 配额控制
  - 密钥轮换

### 4. 服务工厂层 (Service Factory Layer)

#### 4.1 服务工厂 (Service Factory)

- **位置**: `app/services/service_factory.py`
- **职责**: 统一管理所有服务的实例化和依赖注入
- **特性**:
  - 自动依赖注入
  - 服务生命周期管理
  - 健康检查
  - 服务信息查询

## 核心特性

### 1. 统一事务管理

```python
# 使用事务管理器
with tx_manager.transaction("Create model with provider") as session:
    # 执行数据库操作
    model = session.add(LLMModel(...))
    session.flush()
    
    # 创建关联
    association = session.add(LLMModelProvider(...))
    
    # 自动提交或回滚
```

### 2. 重试机制

```python
# 带重试的操作
result = tx_manager.execute_with_retry(
    operation_function,
    max_retries=3,
    description="Database operation"
)
```

### 3. 详细日志记录

```python
# 自动记录事务生命周期
logger.info("🚀 Starting transaction: Create model")
logger.debug("   📍 Session ID: 12345")
logger.debug("   ⏰ Start time: 2024-01-01 10:00:00")
logger.info("✅ Transaction committed successfully")
logger.debug("   ⏱️  Total duration: 150.25ms")
```

### 4. 数据验证

```python
# 自动验证实体存在性
provider = tx_manager.validate_entity_exists(
    session, LLMProvider, provider_id, "Provider"
)

# 检查唯一性约束
tx_manager.check_unique_constraint(
    session, LLMModel, {"name": model_name}, "Model"
)
```

## 使用方式

### 1. 基本使用

```python
from app.services.service_factory import ServiceFactory

# 创建服务工厂
service_factory = ServiceFactory(session_factory)

# 获取服务实例
model_service = service_factory.get_model_service()
provider_service = service_factory.get_provider_service()

# 使用服务
models = model_service.get_all_models()
providers = provider_service.get_all_providers()
```

### 2. 创建模型并关联供应商

```python
from app.models import LLMModelCreate

# 创建模型数据
model_data = LLMModelCreate(
    name="gpt-4",
    llm_type="chat",
    description="OpenAI GPT-4 model",
    provider_id=1,
    provider_weight=10,
    is_provider_preferred=True
)

# 创建模型
result = model_service.create_model(model_data)
```

### 3. 事务操作

```python
# 使用事务管理器执行复杂操作
def complex_operation(session):
    # 多个相关操作
    model = create_model(session)
    provider = create_provider(session)
    association = create_association(session, model.id, provider.id)
    return {"model": model, "provider": provider, "association": association}

result = tx_manager.execute_in_transaction(
    complex_operation,
    "Create model with provider and association"
)
```

## 向后兼容性

重构后的架构保持了与原有代码的完全兼容性：

- 原有的 `db_service` 接口保持不变
- API 端点响应格式保持一致
- 数据库模型和关系保持不变
- 配置和部署方式保持不变

## 性能优化

### 1. 连接池管理

- 自动连接池管理
- 连接复用
- 连接健康检查

### 2. 批量操作

```python
# 批量更新权重
updates = [
    {"association_id": 1, "weight": 20},
    {"association_id": 2, "weight": 30}
]
model_provider_service.bulk_update_weights(updates)
```

### 3. 查询优化

- 延迟加载
- 关联查询优化
- 索引建议

## 监控和调试

### 1. 健康检查

```python
# 检查所有服务状态
health_status = service_factory.health_check()
print(f"Overall status: {health_status['status']}")
```

### 2. 服务信息

```python
# 获取服务详细信息
service_info = service_factory.get_service_info()
print(f"Services: {list(service_info['services'].keys())}")
```

### 3. 日志追踪

- 事务ID追踪
- 操作耗时统计
- 错误堆栈记录
- 性能指标监控

## 扩展指南

### 1. 添加新的仓库

```python
class NewEntityRepository(BaseRepository[NewEntity]):
    def __init__(self, transaction_manager):
        super().__init__(transaction_manager, NewEntity)
    
    def validate_entity(self, entity_data):
        # 实现验证逻辑
        pass
    
    def custom_method(self):
        # 实现自定义方法
        pass
```

### 2. 添加新的业务服务

```python
class NewEntityService:
    def __init__(self, new_entity_repo, other_deps):
        self.new_entity_repo = new_entity_repo
        self.other_deps = other_deps
    
    def business_method(self):
        # 实现业务逻辑
        pass
```

### 3. 注册到服务工厂

```python
def _setup_repositories(self):
    # 添加新仓库
    self._repositories['new_entity'] = NewEntityRepository(self._transaction_manager)

def _setup_business_services(self):
    # 添加新服务
    self._services['new_entity'] = NewEntityService(
        self._repositories['new_entity'],
        other_dependencies
    )
```

## 最佳实践

### 1. 事务管理

- 总是使用事务管理器
- 避免手动管理会话
- 合理设置重试次数

### 2. 错误处理

- 使用统一的异常类型
- 记录详细的错误信息
- 实现优雅的降级策略

### 3. 日志记录

- 使用结构化的日志格式
- 记录关键操作和性能指标
- 避免记录敏感信息

### 4. 性能考虑

- 使用批量操作
- 避免N+1查询问题
- 合理使用缓存

## 总结

重构后的架构提供了：

1. **更好的可维护性**: 清晰的分层结构
2. **更强的可扩展性**: 模块化设计
3. **更高的可靠性**: 统一的事务管理
4. **更好的可观测性**: 详细的日志和监控
5. **完全的向后兼容**: 不影响现有功能

这种架构设计为项目的长期发展奠定了坚实的基础，使得添加新功能、修复问题和性能优化变得更加容易。
