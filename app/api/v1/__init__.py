# Export all v1 version routes
from .chat import chat_router
from .image import image_router
from .models import models_router
from .stats import stats_router
from .database import db_router
from .health import health_router
from .providers import providers_router
from .load_balancing import router as load_balancing_router
from .anthropic import anthropic_router

__all__ = [
    "chat_router", 
    "image_router",
    "models_router", 
    "stats_router", 
    "db_router", 
    "health_router",
    "providers_router",
    "load_balancing_router",
    "anthropic_router"
]
