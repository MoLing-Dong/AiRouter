"""
分页工具模块
提供通用的分页参数、响应模型和工具函数
"""

from typing import TypeVar, Generic, List, Optional, Any
from pydantic import BaseModel, Field
from fastapi import Query
from sqlalchemy.orm import Query as SQLAlchemyQuery
from math import ceil


# ============================================================================
# 分页参数模型
# ============================================================================


class PageParams(BaseModel):
    """分页参数"""

    page: int = Field(default=1, ge=1, description="页码（从1开始）")
    page_size: int = Field(default=10, ge=1, le=100, description="每页数量（最大100）")

    @property
    def offset(self) -> int:
        """计算 SQL offset"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """计算 SQL limit"""
        return self.page_size


def get_page_params(
    page: int = Query(1, ge=1, description="页码（从1开始）"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量（最大100）"),
) -> PageParams:
    """
    FastAPI 依赖注入函数，用于获取分页参数

    用法:
        @router.get("/items")
        async def get_items(page_params: PageParams = Depends(get_page_params)):
            ...
    """
    return PageParams(page=page, page_size=page_size)


# ============================================================================
# 分页响应模型
# ============================================================================

T = TypeVar("T")


class PageInfo(BaseModel):
    """分页信息"""

    page: int = Field(description="当前页码")
    page_size: int = Field(description="每页数量")
    total: int = Field(description="总记录数")
    total_pages: int = Field(description="总页数")
    has_next: bool = Field(description="是否有下一页")
    has_prev: bool = Field(description="是否有上一页")


class PageResponse(BaseModel, Generic[T]):
    """分页响应"""

    items: List[T] = Field(description="数据列表")
    page_info: PageInfo = Field(description="分页信息")

    class Config:
        # 支持泛型
        arbitrary_types_allowed = True


# ============================================================================
# 分页工具函数
# ============================================================================


def paginate_list(
    items: List[T], page: int = 1, page_size: int = 10
) -> PageResponse[T]:
    """
    对 Python 列表进行分页

    Args:
        items: 完整的数据列表
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        分页响应对象

    Example:
        >>> items = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        >>> result = paginate_list(items, page=2, page_size=3)
        >>> result.items
        [4, 5, 6]
    """
    total = len(items)
    total_pages = ceil(total / page_size) if page_size > 0 else 0

    # 计算切片范围
    start = (page - 1) * page_size
    end = start + page_size

    # 获取当前页数据
    page_items = items[start:end]

    return PageResponse(
        items=page_items,
        page_info=PageInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


def paginate_query(
    query: SQLAlchemyQuery, page: int = 1, page_size: int = 10
) -> PageResponse[Any]:
    """
    对 SQLAlchemy Query 进行分页

    Args:
        query: SQLAlchemy Query 对象
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        分页响应对象

    Example:
        >>> query = session.query(Model).filter(...)
        >>> result = paginate_query(query, page=1, page_size=10)
    """
    # 获取总数
    total = query.count()
    total_pages = ceil(total / page_size) if page_size > 0 else 0

    # 计算 offset
    offset = (page - 1) * page_size

    # 获取当前页数据
    items = query.offset(offset).limit(page_size).all()

    return PageResponse(
        items=items,
        page_info=PageInfo(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    )


def paginate_query_with_params(
    query: SQLAlchemyQuery, page_params: PageParams
) -> PageResponse[Any]:
    """
    使用 PageParams 对 SQLAlchemy Query 进行分页

    Args:
        query: SQLAlchemy Query 对象
        page_params: 分页参数对象

    Returns:
        分页响应对象
    """
    return paginate_query(query, page_params.page, page_params.page_size)


# ============================================================================
# 游标分页（适用于大数据量）
# ============================================================================


class CursorPageParams(BaseModel):
    """游标分页参数"""

    cursor: Optional[str] = Field(
        default=None, description="游标（上一页最后一条记录的ID）"
    )
    limit: int = Field(default=10, ge=1, le=100, description="每次获取数量（最大100）")


class CursorPageResponse(BaseModel, Generic[T]):
    """游标分页响应"""

    items: List[T] = Field(description="数据列表")
    next_cursor: Optional[str] = Field(description="下一页游标（None表示没有更多数据）")
    has_more: bool = Field(description="是否有更多数据")

    class Config:
        arbitrary_types_allowed = True


def paginate_cursor(
    query: SQLAlchemyQuery,
    cursor_field: str,
    cursor: Optional[str] = None,
    limit: int = 10,
) -> CursorPageResponse[Any]:
    """
    Cursor pagination (when the data is large and the performance is better)

    Args:
        query: SQLAlchemy Query object
        cursor_field: The cursor field name (usually id or created_at)
        cursor: The current cursor value
        limit: The number of items to fetch each time

    Returns:
        The cursor pagination response object

    Example:
        >>> query = session.query(Model).order_by(Model.id)
        >>> result = paginate_cursor(query, 'id', cursor='100', limit=10)
    """
    # if there is a cursor, add WHERE condition
    if cursor:
        query = query.filter(
            getattr(query.column_descriptions[0]["type"], cursor_field) > cursor
        )

    # 多获取一条，用于判断是否还有更多数据
    items = query.limit(limit + 1).all()

    # 判断是否有更多数据
    has_more = len(items) > limit

    # 如果有更多数据，移除最后一条
    if has_more:
        items = items[:limit]

    # 获取下一页游标
    next_cursor = None
    if has_more and items:
        next_cursor = str(getattr(items[-1], cursor_field))

    return CursorPageResponse(items=items, next_cursor=next_cursor, has_more=has_more)


# ============================================================================
# 辅助函数
# ============================================================================


def create_page_info(page: int, page_size: int, total: int) -> PageInfo:
    """
    Create the pagination information object

    Args:
        page: The current page number
        page_size: 每页数量
        total: The total number of records

    Returns:
        The pagination information object
    """
    total_pages = ceil(total / page_size) if page_size > 0 else 0

    return PageInfo(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )


def validate_page_params(page: int, page_size: int) -> None:
    """
    Validate the pagination parameters

    Args:
        page: 页码
        page_size: 每页数量

    Raises:
        ValueError: 参数不合法时抛出 when the parameters are invalid
    """
    if page < 1:
        raise ValueError("The page number must be greater than or equal to 1")

    if page_size < 1:
        raise ValueError("The quantity per page must be greater than or equal to 1")

    if page_size > 50:
        raise ValueError("The quantity per page cannot exceed 50")
