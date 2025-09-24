#!/usr/bin/env python3
"""
AI Router Application Launcher with multicore support
"""
import os
import uvicorn
from config.settings import settings


if __name__ == "__main__":
    # For streaming support, use single worker mode
    # Multi-worker mode can cause issues with SSE streaming
    workers = 1 if not settings.DEBUG else None

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False if not settings.DEBUG else True,
        log_level=settings.LOG_LEVEL.lower(),
        workers=workers,
        loop="uvloop",
        http="h11",
        backlog=getattr(settings, "BACKLOG", 2048),
        timeout_keep_alive=getattr(
            settings, "TIMEOUT_KEEP_ALIVE", 30
        ),  # 增加keep-alive时间
        # 优化流式响应的配置
        ws_ping_interval=20,
        ws_ping_timeout=20,
        limit_max_requests=None,  # 不限制请求数量
        access_log=settings.DEBUG,  # 开发模式显示访问日志
    )
