# AI路由器 - 智能LLM统一API接口

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

一个基于FastAPI的高性能智能AI路由器，为大型语言模型(LLM)提供统一的API接口，支持多种AI服务提供商，实现智能负载均衡和故障转移。

## 📋 目录

- [🚀 核心特性](#-核心特性)
- [🏗️ 架构设计](#️-架构设计)
- [🛠️ 技术栈](#️-技术栈)
- [🐳 Docker部署](#-docker部署)
- [📦 本地开发](#-本地开发)
- [🔧 配置管理](#-配置管理)
- [📚 API文档](#-api文档)
- [📊 监控和指标](#-监控和指标)
- [🔒 安全特性](#-安全特性)
- [🚀 生产部署](#-生产部署)
- [🔧 故障排除](#-故障排除)
- [🤝 贡献指南](#-贡献指南)
- [📄 许可证](#-许可证)

## 🚀 核心特性

- 🔄 **统一API接口**: 通过统一的OpenAI兼容接口访问多种LLM提供商
- ⚡ **智能负载均衡**: 基于响应时间、成本和成功率的智能负载均衡与故障转移
- 📊 **实时健康监控**: 自动监控API健康状态和性能指标
- 🎯 **多模态支持**: 支持文本生成、多模态输入（图像+文本）和函数调用
- 🚀 **帕累托最优选择**: 从多个模型中智能选择最优模型
- 💰 **成本优化**: 健康检查屏蔽功能，避免昂贵模型的不必要检查
- 🐳 **容器化部署**: 完整的Docker支持，开箱即用
- 🗄️ **数据库支持**: PostgreSQL数据库，支持数据持久化
- 🔧 **动态配置**: 支持运行时动态更新模型配置和API密钥
- 🛡️ **故障转移**: 自动故障检测和智能切换

## 🏗️ 架构设计

### 模型为中心的设计

- **模型为主**: 以模型名称为主键，支持多个提供商
- **动态配置**: 支持不同的云服务厂商模型，支持私有模型和公有模型
- **灵活路由**: 根据模型名称选择不同提供商，可配置权重
- **参数配置**: 支持不同的私有参数配置，如模型权重、超参数等

### 支持的提供商

- **OpenAI**: GPT-4, GPT-3.5-turbo, GPT-4-turbo, GPT-5
- **Anthropic**: Claude-3-sonnet, Claude-3-haiku, Claude-3-opus
- **Volcengine**: 火山引擎模型
- **私有服务器**: 自定义OpenAI兼容API

### 负载均衡策略

- **轮询 (Round Robin)**: 简单的轮询选择
- **加权轮询 (Weighted Round Robin)**: 基于权重的轮询
- **性能优先 (Performance Based)**: 基于响应时间和成功率
- **成本优化 (Cost Optimized)**: 基于成本和性能的平衡
- **帕累托最优 (Pareto Optimal)**: 多目标优化选择

## 🛠️ 技术栈

- **Python 3.10+**: 稳定可靠的Python版本
- **FastAPI**: 高性能的现代Web框架
- **uv**: 极速Python包管理器，比pip快10-100倍
- **PostgreSQL**: 可靠的关系型数据库
- **httpx**: 异步HTTP客户端
- **Docker**: 容器化部署
- **多阶段构建**: 优化的Docker镜像构建
- **非root用户**: 安全的容器运行环境

## 🐳 Docker部署

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少2GB可用内存

### 快速开始

#### 1. 克隆项目

```bash
git clone https://github.com/your-username/AiRouter.git
cd AiRouter
```

> **注意**: API密钥通过数据库管理，无需在此配置

#### 2. 启动服务

##### 方法一：一键部署（推荐）

```bash
# 运行部署脚本
./scripts/setup.sh
```

##### 方法二：手动部署

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 3. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 获取模型列表
curl http://localhost:8000/v1/models
```

### 数据库信息

- **数据库名**: `ai_router`
- **用户名**: `ai_router`
- **密码**: `ai_router_password`
- **端口**: `5432`

## 📦 本地开发

### 开发环境要求

- Python 3.10+
- PostgreSQL 15+
- uv (Python 包管理器)

### 安装 uv

```bash
# 使用 pip 安装 uv
pip install uv

# 或者使用官方安装脚本
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安装依赖

```bash
# 使用 uv 安装依赖
uv sync

# 或者激活虚拟环境后安装
uv venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
uv pip install -e .
```

### 环境变量配置

```bash
# 复制环境变量模板
cp .env.example .env
# 编辑.env文件，填入你的API密钥
```

### 启动开发服务器

```bash
# 启动服务
python run.py

# 或者直接运行
python -m app.main
```

## 🔧 配置管理

### 数据库配置

系统支持通过数据库动态管理API密钥和模型配置：

1. **提供商管理**: 添加和管理不同的AI服务提供商
2. **模型配置**: 为每个模型配置多个提供商和权重
3. **API密钥管理**: 安全的API密钥存储和管理
4. **参数配置**: 模型特定的参数配置

### 模型创建与供应商关联

#### 创建模型（可选供应商关联）

```bash
# 创建模型并关联供应商
curl -X POST "http://localhost:8000/v1/db/models" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "gpt-4",
    "llm_type": "chat",
    "description": "GPT-4 模型",
    "provider_id": 1,
    "provider_weight": 10,
    "is_provider_preferred": true
  }'
```

**响应示例：**

```json
{
  "message": "Model created successfully",
  "id": 1,
  "name": "gpt-4",
  "provider_info": {
    "provider_id": 1,
    "provider_name": "OpenAI",
    "weight": 10,
    "is_preferred": true
  }
}
```

#### 创建模型（仅模型，无供应商关联）

```bash
# 仅创建模型，后续单独配置供应商
curl -X POST "http://localhost:8000/v1/db/models" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "claude-3",
    "llm_type": "chat",
    "description": "Claude-3 模型"
  }'
```

## 📚 API文档

### 核心接口

#### 聊天完成

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "temperature": 0.7,
    "max_tokens": 1000
  }'
```

#### 流式聊天

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4",
    "messages": [
      {"role": "user", "content": "你好"}
    ],
    "stream": true
  }'
```

#### 获取模型列表

```bash
curl http://localhost:8000/v1/models
```

#### 健康检查

```bash
# 整体健康状态
curl http://localhost:8000/health

# 特定模型健康状态
curl http://localhost:8000/v1/health/models/gpt-4

# 提供商健康状态
curl http://localhost:8000/v1/health/providers
```

### 图像生成

#### 创建图像

```bash
curl -X POST "http://localhost:8000/v1/images/generations" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "dall-e-3",
    "prompt": "一只可爱的小猫",
    "n": 1,
    "size": "1024x1024"
  }'
```

#### 编辑图像

```bash
curl -X POST "http://localhost:8000/v1/images/edits" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "dall-e-2",
    "image": "base64_encoded_image",
    "prompt": "添加彩虹背景"
  }'
```

### 管理接口

#### 统计信息

```bash
# 获取路由统计
curl http://localhost:8000/v1/stats

# 获取提供商统计
curl http://localhost:8000/v1/providers/stats/overview

# 获取负载均衡统计
curl http://localhost:8000/v1/load-balancing/statistics
```

#### 配置管理

```bash
# 刷新配置
curl -X POST http://localhost:8000/v1/stats/refresh

# 重置统计
curl -X POST http://localhost:8000/v1/stats/reset

# 清理缓存
curl -X POST http://localhost:8000/v1/models/clear-cache
```

## 📊 监控和指标

### 监控健康检查

系统提供全面的健康检查功能：

- 实时监控各提供商状态
- 自动故障检测和恢复
- 性能指标收集
- 模型可用性监控

### 性能指标

- 响应时间统计
- 成功率监控
- 成本分析
- 使用量统计
- 负载均衡效果

### 监控端点

```bash
# 健康状态概览
curl http://localhost:8000/health

# 模型健康详情
curl http://localhost:8000/v1/health/models/gpt-4

# 提供商性能统计
curl http://localhost:8000/v1/providers/OpenAI/performance

# 负载均衡策略统计
curl http://localhost:8000/v1/load-balancing/statistics
```

## 🔒 安全特性

- **API密钥管理**: 安全的密钥存储和轮换
- **访问控制**: 可配置的访问权限
- **请求限流**: 防止API滥用
- **日志记录**: 完整的请求日志
- **非root用户**: 容器内使用非root用户运行
- **数据加密**: 敏感数据加密存储

## 🚀 生产部署

### 使用生产配置

```bash
# 设置生产环境变量
export DEBUG=false
export DATABASE_URL=postgresql://user:pass@host:5432/db

# 启动生产服务
docker-compose up -d
```

### 性能优化

- 使用多阶段构建的Docker镜像
- PostgreSQL数据持久化
- 健康检查和自动重启
- 资源限制和监控
- 连接池优化

### 高可用部署

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  ai-router:
    image: ai-router:latest
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
    environment:
      - DATABASE_URL=postgresql://user:pass@host:5432/db
```

## 🔧 故障排除

### 常见问题

#### 1. 数据库连接失败

```bash
# 检查数据库状态
docker-compose logs postgres

# 重启数据库服务
docker-compose restart postgres

# 检查连接配置
docker-compose exec ai-router env | grep DATABASE
```

#### 2. API密钥配置错误

```bash
# 检查环境变量
docker-compose exec ai-router env | grep API_KEY

# 通过API添加密钥
curl -X POST "http://localhost:8000/v1/db/providers" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "OpenAI",
    "api_key": "your-api-key",
    "base_url": "https://api.openai.com/v1"
  }'
```

#### 3. 端口冲突

```bash
# 修改docker-compose.yml中的端口映射
ports:
  - "8001:8000"  # 改为其他端口
```

#### 4. 模型不可用

```bash
# 检查模型健康状态
curl http://localhost:8000/v1/health/models/gpt-4

# 刷新模型配置
curl -X POST http://localhost:8000/v1/stats/refresh

# 检查提供商状态
curl http://localhost:8000/v1/health/providers
```

#### 5. 内存不足

```bash
# 检查内存使用
docker stats

# 增加内存限制
services:
  ai-router:
    deploy:
      resources:
        limits:
          memory: 2G
```

### 日志分析

```bash
# 查看应用日志
docker-compose logs -f ai-router

# 查看特定时间段的日志
docker-compose logs --since="2024-01-01T00:00:00" ai-router

# 查看错误日志
docker-compose logs ai-router | grep ERROR
```

## 🤝 贡献指南

### 开发环境设置

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 安装开发依赖 (`uv sync --dev`)
4. 运行测试 (`pytest`)
5. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
6. 推送到分支 (`git push origin feature/AmazingFeature`)
7. 打开 Pull Request

### 代码规范

- 使用 `black` 进行代码格式化
- 使用 `isort` 进行导入排序
- 使用 `flake8` 进行代码检查
- 编写单元测试
- 更新相关文档

### 提交规范

使用约定式提交格式：

```text
feat: 添加新功能
fix: 修复bug
docs: 更新文档
style: 代码格式调整
refactor: 代码重构
test: 添加测试
chore: 构建过程或辅助工具的变动
```

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如果您遇到问题或有建议，请：

1. 查看 [Issues](../../issues)
2. 提交新的 Issue
3. 联系项目维护者
4. 查看 [Wiki](../../wiki) 获取更多文档

## 📈 路线图

- [ ] 支持更多AI提供商（Google Gemini、百度文心等）
- [ ] 添加WebSocket支持
- [ ] 实现分布式部署
- [ ] 添加更多负载均衡算法
- [ ] 支持模型微调接口
- [ ] 添加更多监控指标
- [ ] 实现API版本管理

---

**⭐ 如果这个项目对您有帮助，请给我们一个星标！**
