import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings


def create_app() -> FastAPI:
    """创建FastAPI应用实例"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            settings.APP_DESCRIPTION if hasattr(settings, "APP_DESCRIPTION") else None
        ),
    )

    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.SECURITY.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# 创建应用实例
app = create_app()
