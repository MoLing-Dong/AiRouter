"""
全局异常处理器
统一处理所有异常并返回标准 JSON 格式
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证错误"""
    logger.warning(f"Validation error on {request.url.path}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_200_OK,  # 统一返回 200
        content={
            "success": False,
            "message": "请求参数验证失败",
            "errors": exc.errors(),
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未捕获的异常"""
    error_msg = str(exc).replace("{", "{{").replace("}", "}}")
    logger.error(
        f"Unhandled exception on {request.url.path}: {error_msg}", exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,  # 统一返回 200
        content={
            "success": False,
            "message": f"服务器内部错误: {str(exc)}",
        },
    )


async def value_error_handler(request: Request, exc: ValueError):
    """处理 ValueError"""
    logger.warning(f"ValueError on {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": False,
            "message": str(exc),
        },
    )
