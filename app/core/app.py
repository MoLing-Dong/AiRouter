import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import settings
from app.utils.logging_config import get_factory_logger

# Get logger
logger = get_factory_logger()

def create_app() -> FastAPI:
    """Create FastAPI application instance"""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            settings.APP_DESCRIPTION if hasattr(settings, "APP_DESCRIPTION") else None
        ),
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.SECURITY.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    return app


# Create application instance
app = create_app()
