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

# 复制.env.example文件（如果不存在）
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "📝 复制.env.example文件..."
        cp .env.example .env
        echo "✅ .env文件已从.env.example复制"
    else
        echo "⚠️  .env.example文件不存在，请手动创建.env文件"
    fi
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