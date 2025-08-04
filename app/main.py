import os
import uvicorn
import time
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
from config.settings import settings
from app.core.app import app
from app.core.adapters import adapter_manager
from app.services.router import LoadBalancingStrategy, router
from app.core.routes import register_routes

# 注册路由
register_routes(app)


@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # 启动时初始化
    print(f"🚀 启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    # 从数据库加载模型配置
    print("📊 从数据库加载模型配置...")
    adapter_manager.load_models_from_database()

    # 设置路由器策略
    strategy_name = settings.LOAD_BALANCING.strategy
    try:
        strategy = LoadBalancingStrategy(strategy_name)
        router.set_strategy(strategy)
        print(f"📊 路由策略: {strategy.value}")
    except ValueError:
        print(f"⚠️  无效的路由策略: {strategy_name}，使用默认策略")

    yield

    # 应用关闭时的清理
    print("🛑 关闭应用...")
    await adapter_manager.close_all()


# 设置lifespan事件处理器
app.router.lifespan_context = lifespan


# 健康检查端点
@app.get("/health")
async def health_check():
    """应用健康检查"""
    try:
        # 检查所有适配器的健康状态
        health_status = await adapter_manager.health_check_all()

        # 计算整体健康状态
        healthy_count = sum(
            1 for status in health_status.values() if status == "healthy"
        )
        total_count = len(health_status)

        overall_status = "healthy" if healthy_count == total_count else "degraded"
        if healthy_count == 0:
            overall_status = "unhealthy"

        return {
            "status": overall_status,
            "timestamp": time.time(),
            "models": health_status,
            "healthy_models": healthy_count,
            "total_models": total_count,
            "use_database": adapter_manager.use_database,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e), "timestamp": time.time()},
        )


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
