#!/bin/sh

# AI Router 启动脚本
# 确保应用只启动一次，避免双进程问题

echo "🚀 启动 AI Router..."

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 检查是否已经有进程在运行
if pgrep -f "python.*run.py" > /dev/null; then
    echo "⚠️  检测到已有进程在运行，正在停止..."
    pkill -f "python.*run.py"
    sleep 2
fi

# 检查端口是否被占用
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  端口8000已被占用，正在释放..."
    fuser -k 8000/tcp 2>/dev/null
    sleep 2
fi

# 检测Python环境并启动应用
echo "🔍 检测Python环境..."

# 优先使用uv创建的虚拟环境
if [ -f ".venv/bin/python" ]; then
    echo "✅ 使用uv虚拟环境: .venv/bin/python"
    PYTHON_CMD=".venv/bin/python"
elif [ -f ".venv/bin/activate" ]; then
    echo "✅ 激活uv虚拟环境"
    source .venv/bin/activate
    PYTHON_CMD="python"
elif command -v python3 >/dev/null 2>&1; then
    echo "⚠️  使用系统Python3"
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    echo "⚠️  使用系统Python"
    PYTHON_CMD="python"
else
    echo "❌ 未找到Python解释器"
    exit 1
fi

# 验证Python版本
PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "🐍 Python版本: $PYTHON_VERSION"

if [ "$(echo "$PYTHON_VERSION 3.13" | awk '{print ($1 >= $2)}')" -eq 0 ]; then
    echo "❌ Python版本过低，需要Python 3.13+，当前版本: $PYTHON_VERSION"
    exit 1
fi

# 检查必要的依赖
echo "🔍 检查依赖..."
if ! $PYTHON_CMD -c "import fastapi, uvicorn, pydantic" 2>/dev/null; then
    echo "❌ 缺少必要依赖，请运行: uv sync 或 pip install -r requirements.txt"
    exit 1
fi

# 启动应用
echo "✅ 启动应用..."
echo "📡 服务将在 http://0.0.0.0:8000 启动"
exec $PYTHON_CMD run.py
