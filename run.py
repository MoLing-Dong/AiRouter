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
        ),  # Increase keep-alive time
        # Optimize streaming response configuration
        ws_ping_interval=20,
        ws_ping_timeout=20,
        limit_max_requests=None,  # Do not limit request count
        access_log=settings.DEBUG,  # Development mode display access log
    )
