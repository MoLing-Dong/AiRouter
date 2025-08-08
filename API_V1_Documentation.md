# AiRouter API v1 接口文档

## 概述

AiRouter是一个智能的AI服务路由系统，提供统一的API接口来访问不同的AI提供商服务。本文档描述了v1版本的所有API接口。

## 基础信息

- **基础URL**: `/api/v1`
- **内容类型**: `application/json`
- **认证**: 暂未实现认证机制

## 接口分类

### 1. 聊天接口 (Chat)

#### 1.1 聊天完成

**POST** `/v1/chat/completions`

OpenAI兼容的聊天完成接口，支持流式和非流式响应。

**请求参数:**

```json
{
  "model": "gpt-3.5-turbo",
  "messages": [
    {"role": "user", "content": "你好"}
  ],
  "temperature": 0.7,
  "max_tokens": 1000,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "tools": [],
  "tool_choice": null,
  "stream": false,
  "n": 1,
  "stop": null,
  "logit_bias": null,
  "user": null
}
```

**响应格式:**

```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-3.5-turbo",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "你好！有什么我可以帮助你的吗？"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

#### 1.2 文本嵌入

**POST** `/v1/embeddings`

创建文本嵌入向量。

**请求参数:**

```json
{
  "model": "text-embedding-v1",
  "input": "要嵌入的文本"
}
```

**响应格式:**

```json
{
  "object": "list",
  "data": [
    {
      "object": "embedding",
      "embedding": [0.1, 0.2, ...],
      "index": 0
    }
  ],
  "model": "text-embedding-v1",
  "usage": {
    "prompt_tokens": 5,
    "total_tokens": 5
  }
}
```

### 2. 模型管理 (Models)

#### 2.1 获取模型列表

**GET** `/v1/models/`

获取所有可用的模型列表。

**响应格式:**

```json
{
  "object": "list",
  "data": [
    {
      "id": "gpt-3.5-turbo",
      "object": "model",
      "created": 1677652288,
      "permission": ["openai", "azure"],
      "root": "gpt-3.5-turbo",
      "parent": null,
      "providers_count": 2
    }
  ]
}
```

#### 2.2 获取模型详情

**GET** `/v1/models/{model_name}`

获取指定模型的详细信息。

**响应格式:**

```json
{
  "model_name": "gpt-3.5-turbo",
  "model_type": "chat",
  "max_tokens": 4096,
  "temperature": 0.7,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0,
  "enabled": true,
  "priority": 1,
  "providers": [
    {
      "name": "openai",
      "base_url": "https://api.openai.com",
      "weight": 1.0,
      "health_status": "healthy",
      "metrics": {
        "response_time": 1200,
        "success_rate": 0.98,
        "cost_per_1k_tokens": 0.002,
        "total_requests": 1000,
        "total_tokens": 50000
      }
    }
  ],
  "providers_count": 1,
  "created_at": 1677652288
}
```

#### 2.3 检查模型健康状态

**GET** `/v1/models/{model_name}/health`

检查指定模型的健康状态。

**响应格式:**

```json
{
  "model_name": "gpt-3.5-turbo",
  "status": "healthy",
  "timestamp": 1677652288,
  "providers": {
    "openai": "healthy",
    "azure": "degraded"
  },
  "healthy_providers": 1,
  "total_providers": 2
}
```

### 3. 提供商管理 (Providers)

#### 3.1 获取所有提供商

**GET** `/v1/providers/`

获取所有提供商及其健康状态。

**响应格式:**

```json
{
  "providers": [
    {
      "id": 1,
      "name": "openai",
      "provider_type": "official",
      "official_endpoint": "https://api.openai.com",
      "third_party_endpoint": null,
      "is_enabled": true,
      "health_info": {
        "overall_health": "healthy",
        "average_score": 0.95,
        "total_models": 5,
        "healthy_models": 5
      }
    }
  ]
}
```

#### 3.2 获取顶级提供商

**GET** `/v1/providers/top?limit=5`

获取排名前几的提供商。

**响应格式:**

```json
{
  "top_providers": [
    {
      "rank": 1,
      "provider_name": "openai",
      "average_score": 0.95,
      "overall_health": "healthy",
      "total_models": 5,
      "healthy_models": 5
    }
  ]
}
```

#### 3.3 获取提供商健康状态

**GET** `/v1/providers/{provider_name}/health`

获取指定提供商的健康状态。

#### 3.4 获取提供商性能统计

**GET** `/v1/providers/{provider_name}/performance`

获取指定提供商的性能统计信息。

#### 3.5 获取提供商推荐

**GET** `/v1/providers/recommendations?model_name=gpt-3.5-turbo`

获取提供商推荐列表。

#### 3.6 获取模型最佳提供商

**GET** `/v1/providers/{provider_name}/best-for-model?model_name=gpt-3.5-turbo`

为指定模型获取最佳提供商。

#### 3.7 更新提供商健康状态

**PUT** `/v1/providers/{provider_name}/health`

更新提供商的健康状态。

**请求参数:**

```json
{
  "health_status": "healthy"
}
```

#### 3.8 获取提供商概览统计

**GET** `/v1/providers/stats/overview`

获取提供商概览统计信息。

### 4. 健康检查 (Health)

#### 4.1 系统健康检查

**GET** `/v1/health/`

检查所有可用模型的健康状态。

**响应格式:**

```json
{
  "status": "healthy",
  "timestamp": 1677652288,
  "models": {
    "gpt-3.5-turbo": {
      "status": "healthy",
      "providers": {
        "openai": "healthy"
      },
      "healthy_providers": 1,
      "total_providers": 1
    }
  },
  "healthy_models": 1,
  "total_models": 1,
  "use_database": true
}
```

#### 4.2 获取模型健康状态

**GET** `/v1/health/models`

获取所有模型的健康状态概览。

#### 4.3 获取单个模型健康状态

**GET** `/v1/health/models/{model_name}`

获取单个模型的详细健康状态。

#### 4.4 获取提供商健康状态

**GET** `/v1/health/providers`

获取所有提供商的健康状态。

### 5. 统计管理 (Stats)

#### 5.1 获取路由统计

**GET** `/v1/stats/`

获取路由统计信息。

**响应格式:**

```json
{
  "timestamp": 1677652288,
  "stats": {
    "total_requests": 1000,
    "successful_requests": 980,
    "failed_requests": 20,
    "average_response_time": 1200,
    "models": {
      "gpt-3.5-turbo": {
        "requests": 500,
        "success_rate": 0.98,
        "average_response_time": 1100
      }
    }
  },
  "use_database": true
}
```

#### 5.2 重置统计

**POST** `/v1/stats/stats/reset`

重置路由统计信息。

#### 5.3 刷新配置

**POST** `/v1/stats/refresh`

从数据库刷新模型配置。

### 6. 负载均衡策略 (Load Balancing)

#### 6.1 获取可用策略

**GET** `/v1/load-balancing/strategies`

获取所有可用的负载均衡策略。

#### 6.2 获取模型策略

**GET** `/v1/load-balancing/model/{model_name}/strategies`

获取指定模型的所有供应商策略。

#### 6.3 获取模型-供应商策略

**GET** `/v1/load-balancing/model/{model_name}/provider/{provider_name}/strategy`

获取模型-供应商的负载均衡策略。

#### 6.4 更新模型-供应商策略

**PUT** `/v1/load-balancing/model/{model_name}/provider/{provider_name}/strategy`

更新模型-供应商的负载均衡策略。

**请求参数:**

```json
{
  "strategy": "round_robin",
  "strategy_config": {
    "weight": 1.0
  },
  "priority": 1
}
```

#### 6.5 更新熔断器配置

**PUT** `/v1/load-balancing/model/{model_name}/provider/{provider_name}/circuit-breaker`

更新模型-供应商的熔断器配置。

**请求参数:**

```json
{
  "enabled": true,
  "threshold": 5,
  "timeout": 60
}
```

#### 6.6 获取策略统计

**GET** `/v1/load-balancing/statistics?model_name=gpt-3.5-turbo`

获取策略使用统计。

#### 6.7 获取策略建议

**GET** `/v1/load-balancing/model/{model_name}/recommendations`

获取模型的最佳策略建议。

#### 6.8 测试策略

**POST** `/v1/load-balancing/model/{model_name}/test-strategy`

测试负载均衡策略。

#### 6.9 获取系统信息

**GET** `/v1/load-balancing/info`

获取负载均衡系统信息。

### 7. 数据库管理 (Database)

#### 7.1 获取数据库模型

**GET** `/v1/db/models`

获取数据库中的模型列表。

#### 7.2 创建数据库模型

**POST** `/v1/db/models`

创建数据库模型。

**请求参数:**

```json
{
  "name": "gpt-3.5-turbo",
  "llm_type": "chat",
  "description": "GPT-3.5 Turbo模型",
  "is_enabled": true
}
```

#### 7.3 创建数据库提供商

**POST** `/v1/db/providers`

创建数据库提供商。

**请求参数:**

```json
{
  "name": "openai",
  "provider_type": "official",
  "official_endpoint": "https://api.openai.com",
  "third_party_endpoint": null,
  "is_enabled": true
}
```

#### 7.4 创建模型-提供商关联

**POST** `/v1/db/model-providers`

创建模型-提供商关联。

**请求参数:**

```json
{
  "llm_id": 1,
  "provider_id": 1,
  "is_enabled": true,
  "priority": 1
}
```

#### 7.5 创建模型参数

**POST** `/v1/db/model-params`

创建模型参数。

**请求参数:**

```json
{
  "llm_id": 1,
  "provider_id": 1,
  "param_key": "temperature",
  "param_value": "0.7",
  "description": "温度参数"
}
```

## 错误处理

所有接口都使用标准的HTTP状态码：

- **200**: 成功
- **400**: 请求参数错误
- **404**: 资源不存在
- **500**: 服务器内部错误

错误响应格式：

```json
{
  "detail": "错误描述信息"
}
```

## 流式响应

对于聊天接口，支持流式响应。当设置 `stream=true` 时，响应将使用 Server-Sent Events (SSE) 格式：

```
data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-3.5-turbo", "choices": [{"index": 0, "delta": {"content": "你"}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-3.5-turbo", "choices": [{"index": 0, "delta": {"content": "好"}, "finish_reason": null}]}

data: {"id": "chatcmpl-123", "object": "chat.completion.chunk", "created": 1677652288, "model": "gpt-3.5-turbo", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}

data: [DONE]
```

## 使用示例

### 基本聊天请求

```bash
curl -X POST "http://localhost:8000/api/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

### 获取模型列表

```bash
curl -X GET "http://localhost:8000/api/v1/models/"
```

### 检查系统健康状态

```bash
curl -X GET "http://localhost:8000/api/v1/health/"
```

## 注意事项

1. 所有时间戳都是Unix时间戳（秒）
2. 模型名称必须与系统中配置的模型名称完全匹配
3. 提供商名称必须与系统中配置的提供商名称完全匹配
4. 流式响应需要正确处理SSE格式
5. 数据库管理接口需要相应的权限控制（当前未实现）
