# Docker 部署指南

## 🐳 概述

本项目提供了多种Docker部署方式，包括单阶段构建、多阶段构建和Docker Compose部署。

### 🚀 启动方式

项目使用 `run.py` 作为启动入口，这样可以：
- ✅ 统一配置管理（从 `settings` 读取）
- ✅ 支持环境变量覆盖
- ✅ 更好的错误处理和日志
- ✅ 便于调试和开发

## 📦 构建选项

### 1. 单阶段构建（推荐用于开发）

```bash
# 构建镜像
docker build -t ai-router:latest .

# 运行容器
docker run -d \
  --name ai-router \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  ai-router:latest
```

### 2. 多阶段构建（推荐用于生产）

```bash
# 构建镜像
docker build -f Dockerfile.multi -t ai-router:production .

# 运行容器
docker run -d \
  --name ai-router \
  -p 8000:8000 \
  --env-file .env \
  --restart unless-stopped \
  ai-router:production
```

### 3. 使用构建脚本

```bash
# 给脚本添加执行权限
chmod +x scripts/docker-build.sh

# 构建镜像
./scripts/docker-build.sh build

# 运行容器
./scripts/docker-build.sh run

# 使用docker-compose
./scripts/docker-build.sh compose

# 查看帮助
./scripts/docker-build.sh help
```

## 🚀 Docker Compose 部署

### 快速启动

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 环境变量配置

创建 `.env` 文件：

```bash
# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/database

# 负载均衡配置
LOAD_BALANCING_STRATEGY=performance_based
LOAD_BALANCING_HEALTH_CHECK_INTERVAL=30
LOAD_BALANCING_MAX_RETRIES=3
LOAD_BALANCING_TIMEOUT=30
LOAD_BALANCING_ENABLE_FALLBACK=true
LOAD_BALANCING_ENABLE_COST_OPTIMIZATION=true

# API密钥配置
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GOOGLE_API_KEY=your_google_api_key
AZURE_API_KEY=your_azure_api_key
THIRD_PARTY_API_KEY=your_third_party_api_key
PRIVATE_API_KEY=your_private_api_key
```

## 🔧 优化特性

### 1. 安全性优化

- ✅ 使用非root用户运行
- ✅ 最小化基础镜像
- ✅ 清理构建缓存
- ✅ 移除不必要的依赖

### 2. 性能优化

- ✅ 多阶段构建减少镜像大小
- ✅ 使用 `.dockerignore` 排除不必要文件
- ✅ 优化层缓存
- ✅ 设置合适的环境变量

### 3. 可维护性优化

- ✅ 健康检查
- ✅ 自动重启策略
- ✅ 日志管理
- ✅ 环境变量配置

## 📊 镜像大小对比

| 构建方式   | 镜像大小 | 构建时间 | 适用场景   |
| ---------- | -------- | -------- | ---------- |
| 单阶段构建 | ~200MB   | 快       | 开发环境   |
| 多阶段构建 | ~150MB   | 中等     | 生产环境   |
| Alpine基础 | ~100MB   | 慢       | 最小化部署 |

## 🔍 健康检查

应用提供了健康检查端点：

```bash
# 检查应用状态
curl http://localhost:8000/health

# 预期响应
{
  "status": "healthy",
  "timestamp": 1234567890,
  "models": {...},
  "healthy_models": 2,
  "total_models": 2
}
```

## 📝 日志管理

### 查看容器日志

```bash
# 实时查看日志
docker logs -f ai-router

# 查看最近100行日志
docker logs --tail 100 ai-router

# 查看特定时间段的日志
docker logs --since "2024-01-01T00:00:00" ai-router
```

### 日志文件挂载

```bash
# 挂载日志目录
docker run -d \
  --name ai-router \
  -p 8000:8000 \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  ai-router:latest
```

## 🔄 更新部署

### 1. 零停机更新

```bash
# 构建新镜像
docker build -t ai-router:new .

# 启动新容器
docker run -d \
  --name ai-router-new \
  -p 8001:8000 \
  --env-file .env \
  ai-router:new

# 验证新容器
curl http://localhost:8001/health

# 切换流量（使用负载均衡器或nginx）
# 停止旧容器
docker stop ai-router
docker rm ai-router

# 重命名新容器
docker rename ai-router-new ai-router
```

### 2. 使用Docker Compose更新

```bash
# 重新构建并启动
docker-compose up -d --build

# 或者分步更新
docker-compose build
docker-compose up -d
```

## 🛠️ 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 检查端口占用
   netstat -tlnp | grep 8000
   
   # 使用不同端口
   docker run -p 8001:8000 ai-router:latest
   ```

2. **权限问题**
   ```bash
   # 检查文件权限
   ls -la logs/ data/
   
   # 修复权限
   sudo chown -R 1000:1000 logs/ data/
   ```

3. **环境变量问题**
   ```bash
   # 检查环境变量
   docker exec ai-router env | grep LOAD_BALANCING
   
   # 重新加载环境变量
   docker-compose down
   docker-compose up -d
   ```

### 调试模式

```bash
# 以调试模式运行
docker run -it \
  --name ai-router-debug \
  -p 8000:8000 \
  --env-file .env \
  -e DEBUG=true \
  ai-router:latest
```

## 📈 监控和指标

### 应用指标

- 健康状态：`/health`
- 路由统计：`/admin/routing/stats`
- 模型列表：`/v1/models`

### 容器监控

```bash
# 查看容器资源使用
docker stats ai-router

# 查看容器详细信息
docker inspect ai-router
```

## 🎯 最佳实践

1. **使用标签管理镜像版本**
   ```bash
   docker build -t ai-router:v1.0.0 .
   docker tag ai-router:v1.0.0 ai-router:latest
   ```

2. **定期清理未使用的资源**
   ```bash
   docker system prune -f
   docker image prune -f
   ```

3. **使用数据卷持久化数据**
   ```bash
   docker run -v ai-router-data:/app/data ai-router:latest
   ```

4. **配置日志轮转**
   ```bash
   docker run --log-driver json-file \
     --log-opt max-size=10m \
     --log-opt max-file=3 \
     ai-router:latest
   ``` 