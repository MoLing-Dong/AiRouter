#!/usr/bin/env python3
"""
AI Router Application Launcher with multicore support
"""
import os
import uvicorn
from config.settings import settings


if __name__ == "__main__":
    cpu_count = os.cpu_count() or 1
    # Prefer settings.WORKERS if provided; otherwise min(2*CPU, 8)
    if (
        hasattr(settings, "WORKERS")
        and isinstance(settings.WORKERS, int)
        and settings.WORKERS > 0
    ):
        workers = settings.WORKERS
    else:
        workers = min(2 * cpu_count, 8)

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
        timeout_keep_alive=getattr(settings, "TIMEOUT_KEEP_ALIVE", 5),
    )


