"""
Unified API response model
"""

from typing import TypeVar, Generic, Optional, Any
from pydantic import BaseModel, Field


# Define generic type variable
T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """
    Unified API response encapsulation class

    Examples:
        >>> # Success response
        >>> create_success_response(data={"user": "John"})
        >>> create_success_response(data=[], message="Query successful")

        >>> # Failure response
        >>> create_fail_response(message="User not found")
        >>> create_fail_response(message="Parameter error", code=400)
    """

    success: bool = Field(description="Request whether successful")
    message: Optional[str] = Field(default=None, description="Response message")
    data: Optional[T] = Field(default=None, description="Response data")
    code: Optional[int] = Field(
        default=None, description="Business status code (optional)"
    )

    class Config:
        from_attributes = True


def create_success_response(
    data: Optional[T] = None,
    message: str = "Operation successful",
    code: Optional[int] = None,
) -> ApiResponse[T]:
    """
    Create successful response

    Args:
        data: Response data
        message: Success message
        code: Business status code (optional)

    Returns:
        ApiResponse: Success response object
    """
    return ApiResponse(success=True, message=message, data=data, code=code)


def create_fail_response(
    message: str = "Operation failed",
    data: Optional[T] = None,
    code: Optional[int] = None,
) -> ApiResponse[T]:
    """
    Create failure response

    Args:
        message: Failure message
        data: Response data (optional, for returning error details)
        code: Business status code (optional)

    Returns:
        ApiResponse: Failure response object
    """
    return ApiResponse(success=False, message=message, data=data, code=code)


# For compatibility, add aliases
ApiResponse.success = staticmethod(create_success_response)  # type: ignore
ApiResponse.fail = staticmethod(create_fail_response)  # type: ignore


# ==================== Type aliases (for convenience) ====================

# Generic response type
ApiResponseType = ApiResponse[Any]

# Simple success response (no data)
SuccessResponse = ApiResponse[None]
