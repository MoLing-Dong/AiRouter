#!/usr/bin/env python3
"""
AI Router Application Launcher
"""
import uvicorn
from config.settings import settings


if __name__ == "__main__":
    # 禁用reload功能，避免双进程启动问题
    # 在生产环境中reload功能通常不需要
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # 强制禁用reload
        log_level=settings.LOG_LEVEL.lower(),
    )
 