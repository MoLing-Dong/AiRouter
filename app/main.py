import uvicorn
from contextlib import asynccontextmanager
from config.settings import settings
from app.core.app import app
from app.services import adapter_manager
from app.core.routes import register_routes
from app.utils.logging_config import init_logging, get_app_logger

# Initialize logging system
init_logging()

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

    # Start adapter pool
    logger.info("🔄 Starting adapter pool...")
    from app.services.adapter_pool import adapter_pool

    await adapter_pool.start()

    # Load model configurations from database
    logger.info("📊 Loading model configurations from database...")
    adapter_manager.load_models_from_database()

    # Preload models cache for faster first request
    logger.info("🔥 Preloading models cache...")
    from app.api.v1.models.model_service import model_service

    await model_service.preload_models_cache()

    # Display load balancing strategy information
    logger.info("📊 Load balancing strategy system enabled")

    yield

    # Cleanup on application shutdown
    logger.info("🛑 Shutting down application...")
    await adapter_pool.stop()
    await adapter_manager.close_all()


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
    # 避免双重启动，只在直接运行main.py时启动
    # 正常情况下应该通过run.py启动
    print("⚠️  警告: 请使用 run.py 启动应用，而不是直接运行 main.py")
    print("💡 建议: python run.py")
    
    # 如果一定要直接运行，也禁用reload避免双进程
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,  # 禁用reload避免双进程
        log_level=settings.LOG_LEVEL.lower(),
    )
