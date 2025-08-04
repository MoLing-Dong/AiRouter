#!/bin/bash

# Docker构建脚本
set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker未安装，请先安装Docker"
        exit 1
    fi
}

# 构建镜像
build_image() {
    local dockerfile=${1:-"Dockerfile"}
    local tag=${2:-"ai-router:latest"}
    
    print_message "开始构建Docker镜像..."
    print_message "使用Dockerfile: $dockerfile"
    print_message "镜像标签: $tag"
    
    docker build -f "$dockerfile" -t "$tag" .
    
    if [ $? -eq 0 ]; then
        print_message "Docker镜像构建成功: $tag"
    else
        print_error "Docker镜像构建失败"
        exit 1
    fi
}

# 运行容器
run_container() {
    local image=${1:-"ai-router:latest"}
    local port=${2:-"8000"}
    
    print_message "启动Docker容器..."
    print_message "镜像: $image"
    print_message "端口: $port"
    
    # 停止并删除已存在的容器
    docker stop ai-router 2>/dev/null || true
    docker rm ai-router 2>/dev/null || true
    
    # 运行新容器
    docker run -d \
        --name ai-router \
        -p "$port:8000" \
        --env-file .env \
        --restart unless-stopped \
        -e HOST=0.0.0.0 \
        -e PORT=8000 \
        "$image"
    
    if [ $? -eq 0 ]; then
        print_message "Docker容器启动成功"
        print_message "应用地址: http://localhost:$port"
        print_message "健康检查: http://localhost:$port/health"
    else
        print_error "Docker容器启动失败"
        exit 1
    fi
}

# 使用docker-compose
run_compose() {
    print_message "使用docker-compose启动服务..."
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose未安装，请先安装docker-compose"
        exit 1
    fi
    
    docker-compose up -d
    
    if [ $? -eq 0 ]; then
        print_message "Docker Compose服务启动成功"
        print_message "应用地址: http://localhost:8000"
        print_message "健康检查: http://localhost:8000/health"
    else
        print_error "Docker Compose服务启动失败"
        exit 1
    fi
}

# 显示帮助信息
show_help() {
    echo "Docker构建和运行脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  build [dockerfile] [tag]    构建Docker镜像"
    echo "  run [image] [port]          运行Docker容器"
    echo "  compose                      使用docker-compose启动服务"
    echo "  clean                        清理Docker资源"
    echo "  logs                         查看容器日志"
    echo "  stop                         停止容器"
    echo "  help                         显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 build                    构建默认镜像"
    echo "  $0 build Dockerfile.multi ai-router:multi  构建多阶段镜像"
    echo "  $0 run                      运行默认容器"
    echo "  $0 compose                  使用docker-compose启动"
}

# 清理Docker资源
clean_docker() {
    print_message "清理Docker资源..."
    
    # 停止并删除容器
    docker stop ai-router 2>/dev/null || true
    docker rm ai-router 2>/dev/null || true
    
    # 删除镜像
    docker rmi ai-router:latest 2>/dev/null || true
    
    # 清理未使用的资源
    docker system prune -f
    
    print_message "Docker资源清理完成"
}

# 查看日志
show_logs() {
    print_message "查看容器日志..."
    docker logs -f ai-router
}

# 停止容器
stop_container() {
    print_message "停止容器..."
    docker stop ai-router
    print_message "容器已停止"
}

# 主函数
main() {
    check_docker
    
    case "${1:-help}" in
        "build")
            build_image "$2" "$3"
            ;;
        "run")
            run_container "$2" "$3"
            ;;
        "compose")
            run_compose
            ;;
        "clean")
            clean_docker
            ;;
        "logs")
            show_logs
            ;;
        "stop")
            stop_container
            ;;
        "help"|*)
            show_help
            ;;
    esac
}

# 执行主函数
main "$@" 