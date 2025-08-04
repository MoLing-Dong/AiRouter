#!/usr/bin/env python3
"""
AI路由器应用启动脚本
"""
import uvicorn
from config.settings import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
