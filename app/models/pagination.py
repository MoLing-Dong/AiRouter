"""
通用分页响应模型
可以在任何需要分页的接口中复用
"""

from typing import TypeVar, Generic, List
from pydantic import BaseModel, Field


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    通用分页响应模型
    """

    data: List[T] = Field(description="数据列表")
    total: int = Field(description="总记录数")
    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total_pages: int = Field(description="总页数")
    has_prev: bool = Field(description="是否有上一页")
    has_next: bool = Field(description="是否有下一页")

    class Config:
        # 支持泛型
        arbitrary_types_allowed = True


# 别名，更简洁
PagedData = PaginatedResponse
