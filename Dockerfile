# 使用官方Python镜像作为基础镜像
FROM python:3.11-slim

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app

# 复制依赖文件
COPY --chown=app:app requirements.txt .

# 切换到非root用户
USER app

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY --chown=app:app . .

# 创建必要的目录
RUN mkdir -p /app/logs /app/data

# 暴露端口
EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 设置默认环境变量
ENV HOST=0.0.0.0 \
    PORT=8000 \
    DEBUG=false \
    LOAD_BALANCING_STRATEGY=performance_based

# 启动命令
CMD ["python", "run.py"] 