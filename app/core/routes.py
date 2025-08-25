from fastapi import APIRouter
from app.api.v1 import (
    chat_router, 
    image_router,
    models_router, 
    stats_router, 
    db_router, 
    health_router,
    providers_router,
    anthropic_router
)
from app.api.v1.load_balancing import router as load_balancing_router
from app.api.v1.pool import pool_router
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()

def register_routes(app):
    """Register all routes"""
    
    # Register v1 version routes - These routes already contain the /v1 prefix
    app.include_router(chat_router, tags=["Chat"])
    app.include_router(image_router, tags=["Images"])
    app.include_router(models_router, tags=["Model Management"])
    app.include_router(stats_router, tags=["Statistics"])
    app.include_router(db_router, tags=["Database Management"])
    app.include_router(health_router, tags=["Health Check"])
    app.include_router(anthropic_router, tags=["Anthropic"])
    
    # Register provider management routes
    app.include_router(providers_router, tags=["Provider Management"])
    
    # Register load balancing strategy management routes
    app.include_router(load_balancing_router, tags=["Load Balancing Strategy"])
    
    # Register adapter pool management routes
    app.include_router(pool_router, tags=["Adapter Pool Management"])
