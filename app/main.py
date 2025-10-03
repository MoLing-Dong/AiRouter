import uvicorn
from contextlib import asynccontextmanager
from config.settings import settings
from app.core.app import app
from app.services.adapters import adapter_manager
from app.core.routes import register_routes
from app.utils.logging_config import init_logging, get_app_logger
from sqlalchemy import text
from app.services.database.database_service import db_service

# Initialize logging system
init_logging(
    {
        "console_level": settings.LOG_LEVEL,
        "file_level": "DEBUG",
    }
)

# Register routes
register_routes(app)

# Get logger
logger = get_app_logger()


@asynccontextmanager
async def lifespan(app):
    """Application lifecycle management"""
    # Initialize on startup
    logger.info(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    # Apply performance optimizations
    from app.core.performance import performance_config

    performance_config.log_performance_settings()

    # Database connectivity check (fail-fast)
    try:
        with db_service.get_session() as _session:
            _session.execute(text("SELECT 1"))
        logger.info("✅ Database connectivity check passed")
    except Exception as e:
        logger.error(f"❌ Database connectivity check failed: {e}")
        raise

    # Start adapter pool
    logger.info("🔄 Starting adapter pool...")
    from app.services.adapters.adapter_pool import adapter_pool

    await adapter_pool.start()

    # Load model configurations from database
    logger.info("📊 Loading model configurations from database...")
    adapter_manager.load_models_from_database()

    # Preload models cache for faster first request
    logger.info("🔥 Preloading models cache...")
    from app.api.admin.models.model_service import model_service

    await model_service.preload_models_cache()

    # Display load balancing strategy information
    logger.info("📊 Load balancing strategy system enabled")

    # 启动配置热重载监控
    logger.info("🔄 Starting configuration hot reload monitoring...")
    from app.core.config_hot_reload import (
        config_hot_reload_manager,
        add_config_reload_callback,
    )
    import asyncio

    # 注册配置重载回调
    def on_adapter_config_reload(changes):
        """Adapter configuration reload callback"""
        if any(
            key.startswith(("DATABASE_", "REDIS_", "API_")) for key in changes.keys()
        ):
            logger.info(
                "🔄 Detected adapter related configuration changes, reload adapter..."
            )
            adapter_manager.load_models_from_database()

    add_config_reload_callback("adapter_manager", on_adapter_config_reload)

    # Start configuration file monitoring in the background
    asyncio.create_task(config_hot_reload_manager.start_watching())

    yield

    # Cleanup on application shutdown
    logger.info("🛑 Shutting down application...")

    # Stop configuration hot reload monitoring
    await config_hot_reload_manager.stop_watching()

    await adapter_pool.stop()
    await adapter_manager.close_all()
    # Dispose DB connections
    try:
        db_service.close()
    except Exception:
        pass


# Set lifespan event handler
app.router.lifespan_context = lifespan


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": (
            settings.APP_DESCRIPTION if hasattr(settings, "APP_DESCRIPTION") else None
        ),
        "docs": "/docs",
        "models": "/v1/models",
        "stats": "/v1/stats",
        "load_balancing": "/v1/load-balancing",
        "use_database": adapter_manager.use_database,
        "available_models": len(adapter_manager.get_available_models()),
    }


# If running this file directly
if __name__ == "__main__":
    # Avoid double startup, only start when running main.py directly
    # Normally it should be started through run.py
    print("⚠️  Warning: Please use run.py to start the application, not main.py")
    print("💡 Suggestion: python run.py")

    # If you must run directly, also disable reload to avoid double processes
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # Disable reload to avoid double processes
        log_level=settings.LOG_LEVEL.lower(),
    )
