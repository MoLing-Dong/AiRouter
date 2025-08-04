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

## 📦 安装

### 环境要求

- Python 3.8+
- PostgreSQL

### 安装依赖

```bash
# 安装依赖
pip install -r requirements.txt
```

### 环境变量配置

```shell
# windows
copy .env.example .env
#Linux/MacOS
cp .env.example .env
```

## 🏃‍♂️ 快速开始

### 1. 启动服务器

```bash
python run.py
```

### 2. 初始化数据库

```bash
# 添加测试数据
python scripts/check_database.py add
```

### 3. 测试API

```bash
# 健康检查
curl http://localhost:8000/health

# 获取模型列表
curl http://localhost:8000/v1/models

# 聊天完成
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-turbo",
    "messages": [{"role": "user", "content": "你好"}]
  }'
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

## 🐳 Docker部署

### 构建镜像

```bash
docker build -t ai-router .
```

### 运行容器

```bash
docker run -d \
  --name ai-router \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  ai-router
```

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

---

**AI路由器** - 让AI服务更智能、更高效！ 🚀
