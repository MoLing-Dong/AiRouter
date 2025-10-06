# Services 架构文档

## 📁 目录结构（领域驱动设计）

```
app/services/
├── __init__.py                      # 统一服务导出入口
│
├── model/                           # 🔵 模型领域
│   ├── __init__.py
│   ├── model_service.py             # 模型核心管理服务（CRUD）
│   ├── model_query_service.py       # 模型查询服务（用于API展示）
│   ├── cache_manager.py             # 模型列表缓存管理
│   └── model_provider_service.py    # 模型-提供商关联服务
│
├── capability/                      # 🟢 能力领域
│   ├── __init__.py
│   └── capability_service.py        # 能力管理服务
│
├── provider/                        # 🟠 提供商领域
│   ├── __init__.py
│   └── provider_service.py          # 提供商管理服务
│
├── database/                        # 🔴 数据访问服务层
│   ├── __init__.py
│   ├── database_service.py          # 同步数据库服务
│   ├── async_database_service.py   # 异步数据库服务
│   ├── sqlmodel_database_service.py # SQLModel 数据库服务
│   └── transaction_manager.py       # 事务管理器
│
├── adapters/                        # 🟤 适配器管理服务
│   ├── __init__.py
│   ├── adapter_manager.py           # 适配器管理器
│   ├── adapter_factory.py           # 适配器工厂
│   ├── adapter_pool.py              # 适配器池
│   └── adapter_health_checker.py    # 适配器健康检查
│
├── load_balancing/                  # 🟡 负载均衡服务
│   ├── __init__.py
│   ├── router.py                    # 智能路由器
│   └── load_balancing_strategies.py # 负载均衡策略
│
├── monitoring/                      # 🟣 监控服务
│   ├── __init__.py
│   └── health_check_service.py      # 健康检查服务
│
└── infrastructure/                  # ⚙️ 基础设施服务
    ├── __init__.py
    ├── service_factory.py           # 服务工厂（依赖注入）
    └── service_manager.py           # 服务管理器（服务协调）
```

## 🏗️ 架构设计理念

### 领域驱动设计（DDD）

本项目采用**领域驱动设计（Domain-Driven Design）**的垂直切分方式，而非传统的 MVC 水平切分。

#### 为什么选择 DDD？

1. **业务聚合** - 同一业务领域的代码聚合在一起，便于理解和维护
2. **高内聚低耦合** - 领域内部高内聚，领域之间低耦合
3. **团队协作** - 不同团队可以独立负责不同领域
4. **业务清晰** - 代码组织直接反映业务结构

#### 传统分层 vs DDD

**传统分层（水平切分）：**

```
services/
├── controllers/  # 所有控制器
├── services/     # 所有服务
├── repositories/ # 所有仓储
└── models/       # 所有模型
```

**DDD（垂直切分）：**

```
services/
├── model/        # 模型领域的所有内容
├── capability/   # 能力领域的所有内容
└── provider/     # 提供商领域的所有内容
```

## 🎯 业务领域划分

### 1. Model Domain (模型领域) 🔵

**核心职责：**

- 模型的全生命周期管理
- 模型查询和列表展示
- 模型缓存优化
- 模型与提供商的关联

**服务列表：**

| 服务 | 文件 | 职责 |
|------|------|------|
| `ModelService` | `model_service.py` | 模型的增删改查、状态管理 |
| `ModelQueryService` | `model_query_service.py` | 模型查询、列表构建、性能优化 |
| `ModelsCacheManager` | `cache_manager.py` | 模型列表缓存、命中率统计 |
| `ModelProviderService` | `model_provider_service.py` | 模型与提供商的关联管理 |

**使用示例：**

```python
from app.services.model import (
    ModelService,
    model_query_service,
    models_cache
)

# 获取模型列表（带缓存）
models = model_query_service.get_models_with_capabilities()

# 清理缓存
models_cache.clear_cache()
```

### 2. Capability Domain (能力领域) 🟢

**核心职责：**

- 能力的定义和管理
- 模型能力的关联
- 能力的增删改查

**服务列表：**

| 服务 | 文件 | 职责 |
|------|------|------|
| `CapabilityService` | `capability_service.py` | 能力管理、模型能力关联 |

**使用示例：**

```python
from app.services.capability import capability_service

# 获取所有能力
capabilities = capability_service.get_all_capabilities()

# 为模型添加能力
capability_service.add_model_capability("gpt-4", "vision")
```

### 3. Provider Domain (提供商领域) 🟠

**核心职责：**

- 提供商的管理
- API Key 管理
- 提供商配置

**服务列表：**

| 服务 | 文件 | 职责 |
|------|------|------|
| `ProviderService` | `provider_service.py` | 提供商管理、API Key 管理 |

**使用示例：**

```python
from app.services.provider import ProviderService

provider_service = ProviderService(db_service)

# 获取所有提供商
providers = provider_service.get_all_providers(is_enabled=True)
```

## 🛠️ 支撑服务

### Database Services (数据库服务) 🔴

- 数据持久化
- 事务管理
- ORM 封装

### Adapters (适配器服务) 🟤

- LLM 提供商适配器管理
- 连接池管理
- 健康检查

### Load Balancing (负载均衡) 🟡

- 智能路由
- 负载均衡策略
- 流量分发

### Monitoring (监控服务) 🟣

- 健康检查
- 性能监控
- 可用性检测

### Infrastructure (基础设施) ⚙️

- 服务工厂
- 依赖注入
- 服务协调

## 📦 使用方式

### 方式 1：统一入口导入（推荐）

```python
from app.services import (
    # Model Domain
    ModelService,
    model_query_service,
    models_cache,
    
    # Capability Domain
    capability_service,
    
    # Provider Domain
    ProviderService,
    
    # Infrastructure
    ServiceManager,
    
    # Database
    db_service,
    
    # Adapters
    adapter_manager,
)
```

### 方式 2：直接从领域导入

```python
# 从模型领域导入
from app.services.model import ModelService, models_cache

# 从能力领域导入
from app.services.capability import capability_service

# 从提供商领域导入
from app.services.provider import ProviderService
```

## 🎨 设计原则

1. **领域驱动** - 按业务领域组织，而非技术层次
2. **单一职责** - 每个服务类只负责一个功能领域
3. **高内聚低耦合** - 领域内高内聚，领域间低耦合
4. **依赖倒置** - 依赖于抽象，而非具体实现
5. **开闭原则** - 对扩展开放，对修改关闭

## 📊 架构对比

| 维度 | 传统分层架构 | DDD 领域架构 |
|------|------------|-------------|
| **组织方式** | 按技术层次（水平） | 按业务领域（垂直） |
| **文件查找** | 需要跨多个目录 | 在一个领域目录内 |
| **业务理解** | 需要组合多个层次 | 直接反映业务结构 |
| **团队协作** | 容易冲突 | 领域独立开发 |
| **扩展性** | 修改影响多层 | 领域内部修改 |
| **维护性** | 中等 | 高 |

## 🔄 依赖关系

```
┌─────────────────────────────────────────┐
│         API Layer (路由层)               │
└─────────────────┬───────────────────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
┌─────▼────┐ ┌───▼────┐ ┌────▼─────┐
│  Model   │ │Capability│ │ Provider │
│  Domain  │ │ Domain  │ │  Domain  │
└─────┬────┘ └───┬────┘ └────┬─────┘
      │          │           │
      └──────────┼───────────┘
                 │
      ┌──────────┴───────────┐
      │                      │
┌─────▼──────┐    ┌─────────▼─────────┐
│ Database   │    │ Supporting Services│
│ Services   │    │ Adapters, Monitor │
└────────────┘    └───────────────────┘
```

## ✅ 优势总结

1. **业务清晰** - 代码组织直接反映业务结构
2. **易于维护** - 相关代码聚合在一起
3. **团队协作** - 不同团队负责不同领域
4. **扩展友好** - 新增领域或功能容易扩展
5. **降低耦合** - 领域之间通过接口通信
6. **便于测试** - 领域独立，便于单元测试

## 📚 参考资料

- [Domain-Driven Design (DDD)](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [Vertical Slice Architecture](https://jimmybogard.com/vertical-slice-architecture/)
- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)

---

**最后更新时间：** 2025-10-06  
**架构版本：** v2.0 - DDD 领域驱动设计
