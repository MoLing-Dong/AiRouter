# AI路由器 - 智能LLM统一API接口

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://python.org)
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
- 🐳 **容器化部署**: Alpine Linux轻量级Docker镜像，性能优异
- 🗄️ **高性能数据库**: PostgreSQL + 异步SQLAlchemy + SQLModel现代化ORM
- 🚄 **Redis缓存**: 多层缓存策略，查询性能提升10-100倍
- 🔧 **动态配置**: 支持运行时动态更新模型配置和API密钥
- 🛡️ **故障转移**: 自动故障检测和智能切换
- 📈 **性能监控**: 实时性能分析和批量操作优化

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

- **Python 3.13+**: 最新稳定的Python版本，性能更优
- **FastAPI**: 高性能的现代Web框架
- **SQLModel**: 现代化ORM，结合Pydantic和SQLAlchemy优势
- **异步SQLAlchemy**: 高性能异步数据库操作
- **Redis**: 高性能缓存和会话存储
- **uv**: 极速Python包管理器，比pip快10-100倍
- **PostgreSQL**: 可靠的关系型数据库
- **httpx**: 异步HTTP客户端
- **Docker Alpine**: 轻量级容器化部署
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

- Python 3.13+
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
```

## 🔧 故障排除

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
