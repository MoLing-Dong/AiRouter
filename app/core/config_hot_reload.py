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
                logger.info(f"📁 Add configuration file monitoring: {file_path}")

    def add_watched_file(self, file_path: str | Path):
        """Add configuration files to watch"""
        path = Path(file_path).absolute()
        if path.exists():
            self.watched_files.add(path)
            logger.info(f"📁 Add configuration file monitoring: {path}")
        else:
            logger.warning(f"⚠️ Configuration file does not exist: {path}")

    def add_reload_callback(self, name: str, callback: Callable):
        """Add configuration reload callback function"""
        self.reload_callbacks[name] = callback
        logger.info(f"🔄 Register configuration reload callback: {name}")

    async def reload_settings(self) -> bool:
        """Reload settings"""
        try:
            logger.info("🔄 Start reloading configuration...")

            # Reload environment variables
            if Path(".env").exists():
                from dotenv import load_dotenv

                load_dotenv(override=True)
                logger.info("📄 Reload .env file")

            # Create new settings instance
            new_settings = Settings()

            # Validate new configuration
            await self._validate_new_settings(new_settings)

            # Update global settings
            old_settings = dict(self.settings)
            self.settings.__dict__.update(new_settings.__dict__)

            # Record configuration changes
            changes = self._detect_changes(old_settings, new_settings.__dict__)
            if changes:
                logger.info(f"📊 Detected configuration changes: {changes}")

            # Execute callback function
            await self._execute_reload_callbacks(changes)

            self.last_reload_time = time.time()
            logger.info("✅ Configuration reload completed")
            return True

        except ValidationError as e:
            logger.error(f"❌ Configuration validation failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Configuration reload failed: {e}")
            return False

    async def _validate_new_settings(self, new_settings: Settings):
        """Validate the validity of the new configuration"""
        # Validate database connection
        if new_settings.DATABASE_URL != self.settings.DATABASE_URL:
            logger.info("🔍 Validate new database connection...")
            # Here you can add database connection test

        # 验证Redis连接
        if new_settings.REDIS_URL != self.settings.REDIS_URL:
            logger.info("🔍 Validate new Redis connection...")
            # Here you can add Redis connection test

        # 验证API密钥
        if new_settings.API_KEY != self.settings.API_KEY:
            logger.info("🔍 Validate new API key configuration...")

    def _detect_changes(
        self, old_config: Dict[str, Any], new_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Detect configuration changes"""
        changes = {}

        for key, new_value in new_config.items():
            old_value = old_config.get(key)
            if old_value != new_value:
                changes[key] = {"old": old_value, "new": new_value}

        return changes

    async def _execute_reload_callbacks(self, changes: Dict[str, Any]):
        """Execute configuration reload callback function"""
        for name, callback in self.reload_callbacks.items():
            try:
                logger.info(f"🔄 Execute reload callback: {name}")
                if asyncio.iscoroutinefunction(callback):
                    await callback(changes)
                else:
                    callback(changes)
            except Exception as e:
                logger.error(f"❌ Callback execution failed {name}: {e}")

    async def start_watching(self):
        """Start monitoring configuration file changes"""
        if self.is_watching:
            logger.warning("⚠️ Configuration file monitoring is already running")
            return

        self.is_watching = True
        logger.info("🔍 Start configuration file hot reload monitoring...")

        try:
            async for changes in awatch(
                *self.watched_files, watch_filter=self._should_reload
            ):
                if changes:
                    logger.info(
                        f"📝 Detected file changes: {[str(change[1]) for change in changes]}"
                    )

                    # Anti-shake: avoid frequent reloads
                    await asyncio.sleep(0.5)

                    # Reload configuration
                    await self.reload_settings()

        except Exception as e:
            logger.error(f"❌ Configuration file monitoring exception: {e}")
        finally:
            self.is_watching = False

    def _should_reload(self, change, path: str) -> bool:
        """Determine whether to reload configuration"""
        # Ignore temporary files and backup files
        if path.endswith((".tmp", ".bak", ".swp", "~")):
            return False

        # Ignore hidden files
        if Path(path).name.startswith(".") and not Path(path).name == ".env":
            return False

        # Prevent frequent reloads
        if time.time() - self.last_reload_time < 2.0:
            return False

        return True

    async def stop_watching(self):
        """Stop monitoring configuration files"""
        self.is_watching = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Configuration file monitoring stopped")

    async def manual_reload(self) -> Dict[str, Any]:
        """Manually trigger configuration reload"""
        logger.info("🔄 Manually trigger configuration reload...")
        success = await self.reload_settings()

        return {
            "success": success,
            "timestamp": time.time(),
            "last_reload": self.last_reload_time,
            "watched_files": [str(f) for f in self.watched_files],
            "callbacks": list(self.reload_callbacks.keys()),
        }

    def get_status(self) -> Dict[str, Any]:
        """Get hot reload status"""
        return {
            "is_watching": self.is_watching,
            "last_reload_time": self.last_reload_time,
            "watched_files": [str(f) for f in self.watched_files],
            "callbacks_count": len(self.reload_callbacks),
            "callbacks": list(self.reload_callbacks.keys()),
        }


# Global configuration hot reload manager instance
config_hot_reload_manager = ConfigHotReloadManager()


# Convenient function
async def reload_config() -> Dict[str, Any]:
    """Manually reload configuration"""
    return await config_hot_reload_manager.manual_reload()


def add_config_reload_callback(name: str, callback: Callable):
    """Add configuration reload callback"""
    config_hot_reload_manager.add_reload_callback(name, callback)


def add_watched_config_file(file_path: str | Path):
    """Add watched configuration files"""
    config_hot_reload_manager.add_watched_file(file_path)
