"""
数据库查询辅助函数
提供通用的分页查询、筛选等功能
"""

from typing import TypeVar, List, Optional, Callable, Any
from sqlalchemy.orm import Query, Session
from math import ceil
from app.models import PaginatedResponse
from pydantic import BaseModel


T = TypeVar("T", bound=BaseModel)


def paginated_query(
    session: Session,
    model_class: Any,
    result_class: type[T],
    page: int = 1,
    limit: int = 10,
    filters: Optional[dict] = None,
    order_by: Optional[Any] = None,
    transform_func: Optional[Callable] = None,
) -> PaginatedResponse[T]:
    """
    通用的分页查询函数

    Args:
        session: Database session   
        model_class: SQLAlchemy model class (e.g. LLMModel)
        result_class: Response data class (e.g. ModelItemData)
        page: Page number (starts from 1)
        limit: Number of items per page
        filters: Filter condition dictionary {"is_enabled": True}
        order_by: Sort field (e.g. LLMModel.id.desc())
        transform_func: Custom conversion function, converting database objects to response objects

    Returns:
        PaginatedResponse object

    Example:
        >>> def transform(provider):
        >>>     return ProviderItemData(
        >>>         id=provider.id,
        >>>         name=provider.name,
        >>>         ...
        >>>     )
        >>>
        >>> result = paginated_query(
        >>>     session=session,
        >>>     model_class=LLMProvider,
        >>>     result_class=ProviderItemData,
        >>>     page=1,
        >>>     limit=10,
        >>>     filters={"is_enabled": True},
        >>>     order_by=LLMProvider.id.desc(),
        >>>     transform_func=transform
        >>> )
    """
    # create query
    query = session.query(model_class)

    # apply filter conditions
    if filters:
        for field, value in filters.items():
            if value is not None:
                query = query.filter(getattr(model_class, field) == value)

    # get total number of records
    total = query.count()

    # calculate total number of pages
    total_pages = ceil(total / limit) if limit > 0 else 0

    # apply sorting
    if order_by is not None:
        query = query.order_by(order_by)
    else:
        # default to descending order by id
        if hasattr(model_class, "id"):
            query = query.order_by(model_class.id.desc())

    # pagination
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()

    # convert data
    if transform_func:
        result_items = [transform_func(item) for item in items]
    else:
        # if no conversion function is provided, try to use from_attributes
        result_items = [result_class.model_validate(item) for item in items]

    # build pagination response
    return PaginatedResponse(
        data=result_items,
        total=total,
        page=page,
        page_size=limit,
        total_pages=total_pages,
        has_prev=page > 1,
        has_next=page < total_pages,
    )


def apply_search_filter(
    query: Query,
    model_class: Any,
    search_fields: List[str],
    keyword: Optional[str] = None,
) -> Query:
    """
    Apply search filter

    Args:
        query: SQLAlchemy Query object
        model_class: Model class
        search_fields: List of fields to search ["name", "description"]
        keyword: Search keyword

    Returns:
        Query object with search filter applied

    Example:
        >>> query = session.query(LLMModel)
        >>> query = apply_search_filter(
        >>>     query,
        >>>     LLMModel,
        >>>     ["name", "description"],
        >>>     "gpt"
        >>> )
    """
    if not keyword or not search_fields:
        return query

    # Build OR conditions
    from sqlalchemy import or_

    conditions = []
    for field in search_fields:
        if hasattr(model_class, field):
            conditions.append(getattr(model_class, field).like(f"%{keyword}%"))

    if conditions:
        query = query.filter(or_(*conditions))

    return query


def apply_date_range_filter(
    query: Query,
    model_class: Any,
    date_field: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Query:
    """
    Apply date range filter

    Args:
        query: SQLAlchemy Query object
        model_class: Model class
        date_field: Date field name (e.g. "created_at")
        start_date: Start date
        end_date: End date

    Returns:
        Query object with date range filter applied
    """
    if not hasattr(model_class, date_field):
        return query

    field = getattr(model_class, date_field)

    if start_date:
        query = query.filter(field >= start_date)

    if end_date:
        query = query.filter(field <= end_date)

    return query


def apply_sorting(
    query: Query,
    model_class: Any,
    sort_by: Optional[str] = None,
    order: str = "desc",
) -> Query:
    """
    Apply sorting

    Args:
        query: SQLAlchemy Query object
        model_class: Model class
        sort_by: Sort field name
        order: Sort direction "asc" or "desc"

    Returns:
        Query object with sorting applied
    """
    if not sort_by:
        # default to descending order by id
        if hasattr(model_class, "id"):
            return query.order_by(model_class.id.desc())
        return query

    if not hasattr(model_class, sort_by):
        return query

    field = getattr(model_class, sort_by)

    if order.lower() == "asc":
        query = query.order_by(field.asc())
    else:
        query = query.order_by(field.desc())

    return query
