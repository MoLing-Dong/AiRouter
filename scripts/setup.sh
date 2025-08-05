#!/bin/bash

# AI Router 部署脚本
# 使用方法: ./scripts/setup.sh

set -e

echo "🚀 AI Router 部署脚本"
echo "========================"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

# 创建.env文件（如果不存在）
if [ ! -f .env ]; then
    echo "📝 创建.env文件..."
    cat > .env << 'EOF'
# ========================================
# AI Router 环境变量配置（可选）
# ========================================

# 应用配置
DEBUG=false
HOST=0.0.0.0
PORT=8000

# 可选：自定义配置
LOAD_BALANCING_STRATEGY=performance_based
SECURITY_RATE_LIMIT=100
MONITORING_ENABLED=true
EOF
    echo "✅ .env文件已创建（API密钥通过数据库管理）"
else
    echo "✅ .env文件已存在"
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p logs data

# 构建并启动服务
echo "🔨 构建Docker镜像..."
docker-compose build

echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

# 健康检查
echo "🏥 执行健康检查..."
if curl -f http://localhost:8000/health &> /dev/null; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "🌐 访问地址: http://localhost:8000"
    echo "📊 健康检查: http://localhost:8000/health"
    echo "📋 API文档: http://localhost:8000/docs"
    echo ""
    echo "📝 常用命令:"
    echo "  查看日志: docker-compose logs -f"
    echo "  停止服务: docker-compose down"
    echo "  重启服务: docker-compose restart"
else
    echo "❌ 服务启动失败，请检查日志:"
    docker-compose logs ai-router
fi 