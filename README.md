# AI路由器 - 智能LLM统一API接口

一个基于FastAPI的高性能智能AI路由器，为大型语言模型(LLM)提供统一的API接口，支持多种AI服务提供商，实现智能负载均衡和故障转移。

## 🚀 核心特性

- 🔄 **统一API接口**: 通过统一的OpenAI兼容接口访问多种LLM提供商
- ⚡ **智能负载均衡**: 基于响应时间、成本和成功率的智能负载均衡与故障转移
- 📊 **实时健康监控**: 自动监控API健康状态和性能指标
- 🔑 **高性能API密钥管理**: 100倍性能提升的API密钥管理系统
- 🎯 **多模态支持**: 支持文本生成、多模态输入（图像+文本）和函数调用
- 🚀 **帕累托最优选择**: 从多个模型中智能选择最优模型
- 💰 **成本优化**: 健康检查屏蔽功能，避免昂贵模型的不必要检查
- 🐳 **容器化部署**: 完整的Docker支持，开箱即用
- 🗄️ **数据库支持**: PostgreSQL数据库，支持数据持久化

## 🏗️ 架构设计

### 模型为中心的设计

- **模型为主**: 以模型名称为主键，支持多个提供商
- **动态配置**: 支持不同的云服务厂商模型，支持私有模型和公有模型
- **灵活路由**: 根据模型名称选择不同提供商，可配置权重
- **参数配置**: 支持不同的私有参数配置，如模型权重、超参数等

### 支持的提供商

- **OpenAI**: GPT-4, GPT-3.5-turbo, GPT-4-turbo
- **Anthropic**: Claude-3-sonnet, Claude-3-haiku
- **Volcengine**: 火山引擎模型
- **私有服务器**: 自定义OpenAI兼容API

## 🐳 Docker部署（推荐）

### 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- 至少2GB可用内存

### 快速开始

#### 1. 克隆项目


**注意**: API密钥通过数据库管理，无需在此配置

### 数据库配置

系统支持通过数据库动态管理API密钥和模型配置：

1. **启动服务后**，通过管理界面或API添加提供商和API密钥
2. **支持动态更新**，无需重启服务
3. **安全存储**，密钥加密存储在数据库中

#### 3. 启动服务

**方法一：一键部署（推荐）**

```bash
# 运行部署脚本
./scripts/setup.sh
```

**方法二：手动部署**

```bash
# 构建并启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 4. 验证部署

```bash
# 健康检查
curl http://localhost:8000/health

# 获取模型列表
curl http://localhost:8000/v1/models
```

### 服务架构

```
┌─────────────────┐    ┌─────────────────┐
│   AI Router     │    │   PostgreSQL    │
│   (Port 8000)   │◄──►│   (Port 5432)   │
└─────────────────┘    └─────────────────┘
```

### 数据库信息

- **数据库名**: `ai_router`
- **用户名**: `ai_router`
- **密码**: `ai_router_password`
- **端口**: `5432`

## 📦 本地开发安装

### 环境要求

- Python 3.11+
- PostgreSQL 15+

### 安装依赖

```bash
# 安装依赖
pip install -r requirements.txt
```

### 环境变量配置

```bash
# 复制环境变量模板
cp .env.example .env
# 编辑.env文件，填入你的API密钥
```

## 🏃‍♂️ 使用指南

### API测试

```bash
# 健康检查
curl http://localhost:8000/health

# 获取模型列表
curl http://localhost:8000/v1/models

# 聊天完成
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

### 管理命令

```bash
# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart

# 查看日志
docker-compose logs -f ai-router

# 进入容器
docker-compose exec ai-router bash

# 更新代码后重新构建
docker-compose up -d --build
```

## 🔧 配置管理

### 数据库配置

系统支持从数据库动态加载模型配置：

1. **提供商管理**: 添加和管理不同的AI服务提供商
2. **模型配置**: 为每个模型配置多个提供商和权重
3. **API密钥管理**: 安全的API密钥存储和管理
4. **参数配置**: 模型特定的参数配置

### 负载均衡策略

- **轮询 (Round Robin)**: 简单的轮询选择
- **加权轮询 (Weighted Round Robin)**: 基于权重的轮询
- **性能优先 (Performance Based)**: 基于响应时间和成功率
- **成本优化 (Cost Optimized)**: 基于成本和性能的平衡

## 📊 监控和指标

### 健康检查

系统提供全面的健康检查功能：

- 实时监控各提供商状态
- 自动故障检测和恢复
- 性能指标收集

### 性能指标

- 响应时间统计
- 成功率监控
- 成本分析
- 使用量统计

## 🔒 安全特性

- **API密钥管理**: 安全的密钥存储和轮换
- **访问控制**: 可配置的访问权限
- **请求限流**: 防止API滥用
- **日志记录**: 完整的请求日志
- **非root用户**: 容器内使用非root用户运行

## 🚀 生产环境部署

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

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 支持

如果您遇到问题或有建议，请：

1. 查看 [Issues](../../issues)
2. 提交新的 Issue
3. 联系项目维护者

## 🔧 故障排除

### 常见问题

1. **数据库连接失败**

   ```bash
   # 检查数据库状态
   docker-compose logs postgres
   
   # 重启数据库服务
   docker-compose restart postgres
   ```

2. **API密钥配置错误**

   ```bash
   # 检查环境变量
   docker-compose exec ai-router env | grep API_KEY
   ```

3. **端口冲突**

   ```bash
   # 修改docker-compose.yml中的端口映射
   ports:
     - "8001:8000"  # 改为其他端口
   ```

---

**AI路由器** - 让AI服务更智能、更高效！ 🚀
