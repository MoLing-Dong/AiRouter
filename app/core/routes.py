from fastapi import APIRouter
from app.api.v1 import v1_router
from app.api.admin import admin_router
from app.api.api import api_router
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()


def register_routes(app):
    """Register all routes"""

    # Register v1 API routes (core AI services)
    app.include_router(v1_router)

    # Register admin routes (management/utility APIs)
    app.include_router(admin_router)

    # Register API routes (other business APIs)
    app.include_router(api_router)
