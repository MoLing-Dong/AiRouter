import uvicorn
import time
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from config.settings import settings
from app.core.app import app
from app.services import adapter_manager
from app.core.routes import register_routes

# 注册路由
register_routes(app)


@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # 启动时初始化
    print(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    # 启动适配器池
    print("🔄 启动适配器池...")
    from app.services.adapter_pool import adapter_pool
    await adapter_pool.start()

    # 从数据库加载模型配置
    print("📊 从数据库加载模型配置...")
    adapter_manager.load_models_from_database()

    # 显示负载均衡策略信息
    print("📊 负载均衡策略系统已启用")
    print(f"📊 支持策略: auto, specified_provider, fallback, weighted_round_robin, least_connections, response_time, cost_optimized, hybrid")

    yield

    # 应用关闭时的清理
    print("🛑 关闭应用...")
    await adapter_pool.stop()
    await adapter_manager.close_all()


# 设置lifespan事件处理器
app.router.lifespan_context = lifespan


# 根端点
@app.get("/")
async def root():
    """根端点"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "description": (
            settings.APP_DESCRIPTION if hasattr(settings, "APP_DESCRIPTION") else None
        ),
        "docs": "/docs",
        "health": "/health",
        "models": "/v1/models",
        "stats": "/v1/stats",
        "load_balancing": "/v1/load-balancing",
        "use_database": adapter_manager.use_database,
        "available_models": len(adapter_manager.get_available_models()),
    }


# 如果直接运行此文件
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
    )
