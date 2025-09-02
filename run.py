#!/usr/bin/env python3
"""
AI Router Application Launcher with multicore support
"""
import os
import uvicorn
from config.settings import settings


if __name__ == "__main__":
    # 建议设置为 CPU 核心数（生产环境），开发环境可设为 1
    workers = settings.WORKERS if hasattr(settings, "WORKERS") else os.cpu_count()

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        workers=workers,  # 启用多进程，利用多核
    )
