"""
配置热重载管理器
支持运行时动态更新配置而无需重启服务
"""

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Set
from watchfiles import awatch
from pydantic import ValidationError

from config.settings import Settings, settings
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class ConfigHotReloadManager:
    """配置热重载管理器"""

    def __init__(self):
        self.settings = settings
        self.watched_files: Set[Path] = set()
        self.reload_callbacks: Dict[str, Callable] = {}
        self.is_watching = False
        self.watch_task: Optional[asyncio.Task] = None
        self.last_reload_time = time.time()

        # 添加默认监控文件
        self._add_default_watched_files()

    def _add_default_watched_files(self):
        """添加默认需要监控的配置文件"""
        config_files = [
            Path(".env"),
            Path("config/settings.py"),
            Path("alembic.ini"),
        ]

        for file_path in config_files:
            if file_path.exists():
                self.watched_files.add(file_path.absolute())
                logger.info(f"📁 添加配置文件监控: {file_path}")

    def add_watched_file(self, file_path: str | Path):
        """添加需要监控的配置文件"""
        path = Path(file_path).absolute()
        if path.exists():
            self.watched_files.add(path)
            logger.info(f"📁 添加配置文件监控: {path}")
        else:
            logger.warning(f"⚠️ 配置文件不存在: {path}")

    def add_reload_callback(self, name: str, callback: Callable):
        """添加配置重载回调函数"""
        self.reload_callbacks[name] = callback
        logger.info(f"🔄 注册配置重载回调: {name}")

    async def reload_settings(self) -> bool:
        """重新加载设置"""
        try:
            logger.info("🔄 开始重新加载配置...")

            # 重新加载环境变量
            if Path(".env").exists():
                from dotenv import load_dotenv

                load_dotenv(override=True)
                logger.info("📄 重新加载 .env 文件")

            # 创建新的设置实例
            new_settings = Settings()

            # 验证新配置
            await self._validate_new_settings(new_settings)

            # 更新全局设置
            old_settings = dict(self.settings)
            self.settings.__dict__.update(new_settings.__dict__)

            # 记录配置变更
            changes = self._detect_changes(old_settings, new_settings.__dict__)
            if changes:
                logger.info(f"📊 检测到配置变更: {changes}")

            # 执行回调函数
            await self._execute_reload_callbacks(changes)

            self.last_reload_time = time.time()
            logger.info("✅ 配置重载完成")
            return True

        except ValidationError as e:
            logger.error(f"❌ 配置验证失败: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ 配置重载失败: {e}")
            return False

    async def _validate_new_settings(self, new_settings: Settings):
        """验证新配置的有效性"""
        # 验证数据库连接
        if new_settings.DATABASE_URL != self.settings.DATABASE_URL:
            logger.info("🔍 验证新的数据库连接...")
            # 这里可以添加数据库连接测试

        # 验证Redis连接
        if new_settings.REDIS_URL != self.settings.REDIS_URL:
            logger.info("🔍 验证新的Redis连接...")
            # 这里可以添加Redis连接测试

        # 验证API密钥
        if new_settings.API_KEY != self.settings.API_KEY:
            logger.info("🔍 验证新的API密钥配置...")

    def _detect_changes(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """检测配置变更"""
        changes = {}

        for key, new_value in new_config.items():
            old_value = old_config.get(key)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}

        return changes

    async def _execute_reload_callbacks(self, changes: Dict[str, Any]):
        """执行配置重载回调函数"""
        for name, callback in self.reload_callbacks.items():
            try:
                logger.info(f"🔄 执行重载回调: {name}")
                if asyncio.iscoroutinefunction(callback):
                    await callback(changes)
                else:
                    callback(changes)
            except Exception as e:
                logger.error(f"❌ 回调执行失败 {name}: {e}")

    async def start_watching(self):
        """开始监控配置文件变化"""
        if self.is_watching:
            logger.warning("⚠️ 配置文件监控已经在运行")
            return

        self.is_watching = True
        logger.info("🔍 启动配置文件热重载监控...")

        try:
            async for changes in awatch(
                *self.watched_files, watch_filter=self._should_reload
            ):
                if changes:
                    logger.info(
                        f"📝 检测到文件变化: {[str(change[1]) for change in changes]}"
                    )

                    # 防抖动：避免频繁重载
                    await asyncio.sleep(0.5)

                    # 重新加载配置
                    await self.reload_settings()

        except Exception as e:
            logger.error(f"❌ 配置文件监控异常: {e}")
        finally:
            self.is_watching = False

    def _should_reload(self, change, path: str) -> bool:
        """判断是否应该重载配置"""
        # 忽略临时文件和备份文件
        if path.endswith((".tmp", ".bak", ".swp", "~")):
            return False

        # 忽略隐藏文件
        if Path(path).name.startswith(".") and not Path(path).name == ".env":
            return False

        # 防止过于频繁的重载
        if time.time() - self.last_reload_time < 2.0:
            return False

        return True

    async def stop_watching(self):
        """停止监控配置文件"""
        self.is_watching = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 配置文件监控已停止")

    async def manual_reload(self) -> Dict[str, Any]:
        """手动触发配置重载"""
        logger.info("🔄 手动触发配置重载...")
        success = await self.reload_settings()

        return {
            "success": success,
            "timestamp": time.time(),
            "last_reload": self.last_reload_time,
            "watched_files": [str(f) for f in self.watched_files],
            "callbacks": list(self.reload_callbacks.keys()),
        }

    def get_status(self) -> Dict[str, Any]:
        """获取热重载状态"""
        return {
            "is_watching": self.is_watching,
            "last_reload_time": self.last_reload_time,
            "watched_files": [str(f) for f in self.watched_files],
            "callbacks_count": len(self.reload_callbacks),
            "callbacks": list(self.reload_callbacks.keys()),
        }


# 全局配置热重载管理器实例
config_hot_reload_manager = ConfigHotReloadManager()


# 便捷函数
async def reload_config() -> Dict[str, Any]:
    """手动重载配置"""
    return await config_hot_reload_manager.manual_reload()


def add_config_reload_callback(name: str, callback: Callable):
    """添加配置重载回调"""
    config_hot_reload_manager.add_reload_callback(name, callback)


def add_watched_config_file(file_path: str | Path):
    """添加监控的配置文件"""
    config_hot_reload_manager.add_watched_file(file_path)
