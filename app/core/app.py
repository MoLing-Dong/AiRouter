import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from config.settings import settings
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


def create_app() -> FastAPI:
    """Create FastAPI application instance"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            settings.APP_DESCRIPTION if hasattr(settings, "APP_DESCRIPTION") else None
        ),
    )

    # ==================== 注册异常处理器 ====================
    from app.middleware import (
        validation_exception_handler,
        general_exception_handler,
        value_error_handler,
    )

    # 请求验证错误
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # ValueError
    app.add_exception_handler(ValueError, value_error_handler)
    # 所有其他异常
    app.add_exception_handler(Exception, general_exception_handler)

    # ==================== 注册中间件 ====================
    # 请求日志中间件
    from app.middleware import RequestLoggingMiddleware

    app.add_middleware(RequestLoggingMiddleware)

    # CORS 中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.SECURITY.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create application instance
app = create_app()
