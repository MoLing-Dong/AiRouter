"""
统一的 API 响应模型
提供类似 Java Result 的响应封装结构
"""

from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel, Field


# 定义泛型类型变量
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    统一的 API 响应封装类

    Examples:
        >>> # 成功响应
        >>> create_success_response(data={"user": "John"})
        >>> create_success_response(data=[], message="查询成功")

        >>> # 失败响应
        >>> create_fail_response(message="用户不存在")
        >>> create_fail_response(message="参数错误", code=400)
    """

    success: bool = Field(description="请求是否成功")
    message: Optional[str] = Field(default=None, description="响应消息")
    data: Optional[T] = Field(default=None, description="响应数据")
    code: Optional[int] = Field(default=None, description="业务状态码（可选）")

    class Config:
        from_attributes = True


# 工厂函数（替代 classmethod）
def create_success_response(
    data: Optional[T] = None,
    message: str = "操作成功",
    code: Optional[int] = None,
) -> ApiResponse[T]:
    """
    创建成功响应

    Args:
        data: 响应数据
        message: 成功消息
        code: 业务状态码（可选）

    Returns:
        ApiResponse: 成功响应对象
    """
    return ApiResponse(success=True, message=message, data=data, code=code)


def create_fail_response(
    message: str = "操作失败",
    data: Optional[T] = None,
    code: Optional[int] = None,
) -> ApiResponse[T]:
    """
    创建失败响应

    Args:
        message: 失败消息
        data: 响应数据（可选，用于返回错误详情）
        code: 业务状态码（可选）

    Returns:
        ApiResponse: 失败响应对象
    """
    return ApiResponse(success=False, message=message, data=data, code=code)


# 为了兼容性，添加别名
ApiResponse.success = staticmethod(create_success_response)  # type: ignore
ApiResponse.fail = staticmethod(create_fail_response)  # type: ignore


# ==================== 类型别名（便于使用） ====================

# 通用响应类型
ApiResponseType = ApiResponse[Any]

# 简单成功响应（无数据）
SuccessResponse = ApiResponse[None]
