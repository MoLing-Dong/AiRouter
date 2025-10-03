from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import time
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件 - 记录所有请求"""

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()

        # 记录请求开始
        logger.info(f"➡️  {request.method} {request.url.path}")

        # 执行请求
        response = await call_next(request)

        # 计算耗时
        process_time = time.time() - start_time

        # 记录请求完成
        logger.info(
            f"⬅️  {request.method} {request.url.path} "
            f"Status: {response.status_code} Time: {process_time:.3f}s"
        )

        # 添加响应头
        response.headers["X-Process-Time"] = str(process_time)

        return response


class ResponseFormatMiddleware(BaseHTTPMiddleware):
    """响应格式化中间件 - 统一响应格式（可选）"""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # 这里可以统一处理响应格式
        # 例如：添加通用的响应头、包装响应体等

        return response
