#!/bin/bash

# AI Router 启动脚本
# 确保应用只启动一次，避免双进程问题

echo "🚀 启动 AI Router..."

# 检查是否已经有进程在运行
if pgrep -f "python.*run.py" > /dev/null; then
    echo "⚠️  检测到已有进程在运行，正在停止..."
    pkill -f "python.*run.py"
    sleep 2
fi

# 检查端口是否被占用
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  端口8000已被占用，正在释放..."
    fuser -k 8000/tcp
    sleep 2
fi

# 启动应用
echo "✅ 启动应用..."
python run.py

echo "🎉 应用已启动完成！"
