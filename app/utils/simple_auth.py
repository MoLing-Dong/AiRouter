"""
简单的API密钥认证工具
专门用于保护业务API端点（如chat接口）
"""

import os
from typing import Optional
from fastapi import HTTPException, status, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from config.settings import settings
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()

# HTTP Bearer 安全方案
security = HTTPBearer(auto_error=False)


def get_api_key_from_request(request: Request) -> Optional[str]:
    """
    从请求中提取API密钥
    只支持 Authorization: Bearer token 方式
    """
    # 从 Authorization 头获取 (Bearer token)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def get_valid_api_keys() -> set:
    """
    获取有效的API密钥集合
    从环境变量中读取
    """
    api_keys = set()

    # 支持多种环境变量名称
    env_keys = [
        "API_KEY",
        "API_KEYS",
    ]

    # 首先从settings获取
    if hasattr(settings, "API_KEY") and settings.API_KEY:
        keys = [k.strip() for k in settings.API_KEY.split(",") if k.strip()]
        api_keys.update(keys)

    # 然后从环境变量获取
    for env_key in env_keys:
        value = os.getenv(env_key)
        if value:
            # 支持逗号分隔的多个密钥
            keys = [k.strip() for k in value.split(",") if k.strip()]
            api_keys.update(keys)

    return api_keys


def validate_api_key(api_key: str) -> bool:
    """
    验证API密钥是否有效
    """
    if not api_key:
        return False

    # 获取有效的API密钥集合
    valid_keys = get_valid_api_keys()

    # 如果没有配置任何API密钥，则允许访问（开发模式）
    if not valid_keys:
        logger.warning("⚠️ 未配置API密钥，允许所有请求访问")
        return True

    return api_key in valid_keys


def require_api_key(request: Request) -> str:
    """
    FastAPI依赖项：要求提供有效的API密钥
    用于保护需要认证的端点
    """
    # 检查是否启用API密钥认证
    if not settings.SECURITY.api_key_required:
        logger.debug("🔓 API密钥认证已禁用")
        return "disabled"

    # 提取API密钥
    api_key = get_api_key_from_request(request)

    if not api_key:
        logger.warning(
            f"🚫 API密钥缺失 - IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "API密钥缺失",
                "message": "请在请求头中提供有效的API密钥",
                "method": "在请求头中添加: Authorization: Bearer your-api-key",
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 验证API密钥
    if not validate_api_key(api_key):
        logger.warning(
            f"🚫 API密钥无效: {api_key[:8]}*** - IP: {request.client.host if request.client else 'unknown'}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "API密钥无效", "message": "提供的API密钥无效或已过期"},
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 记录成功的认证
    logger.info(
        f"✅ API密钥认证成功: {api_key[:8]}*** - IP: {request.client.host if request.client else 'unknown'}"
    )

    return api_key


def optional_api_key(request: Request) -> Optional[str]:
    """
    FastAPI依赖项：可选的API密钥
    用于可以选择性认证的端点
    """
    if not settings.SECURITY.api_key_required:
        return None

    api_key = get_api_key_from_request(request)

    if api_key and validate_api_key(api_key):
        logger.info(f"✅ 可选API密钥认证成功: {api_key[:8]}***")
        return api_key

    return None


def generate_api_key() -> str:
    """
    生成新的API密钥
    """
    import secrets
    import string

    # 生成32字符的随机API密钥
    alphabet = string.ascii_letters + string.digits
    api_key = "".join(secrets.choice(alphabet) for _ in range(32))

    logger.info(f"🔑 生成新的API密钥: {api_key[:8]}***")

    return api_key


def get_auth_status() -> dict:
    """
    获取认证系统状态
    """
    valid_keys = get_valid_api_keys()

    return {
        "authentication_enabled": settings.SECURITY.api_key_required,
        "configured_keys_count": len(valid_keys),
        "has_keys_configured": len(valid_keys) > 0,
        "supported_method": "Authorization Bearer token",
    }
