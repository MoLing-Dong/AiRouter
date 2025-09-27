import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from config.settings import settings


class LogConfig:
    """Logging configuration class"""

    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)

        # Log file path
        self.log_file = (
            self.log_dir / f"ai_router_{datetime.now().strftime('%Y%m%d')}.log"
        )
        self.error_file = (
            self.log_dir / f"ai_router_error_{datetime.now().strftime('%Y%m%d')}.log"
        )

        # Get environment variable
        self.run_env = settings.RUN_ENV

        # Development environment log format (detailed format)
        self.dev_console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <5}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )

        # Production environment log format (simple format)
        self.prod_console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <5}</level> | "
            "<level>{message}</level>"
        )

        # 简洁的文件日志格式（移除文件位置信息）
        self.file_format = "{time:YYYY-MM-DD HH:mm:ss} | " "{level: <5} | " "{message}"

        # Log levels
        self.console_level = "INFO"
        self.file_level = "DEBUG"
        self.error_level = "ERROR"

    def setup_logging(
        self,
        console_level: str = "INFO",
        file_level: str = "DEBUG",
        enable_console: bool = True,
        enable_file: bool = True,
        max_file_size: str = "10 MB",
        rotation: str = "1 day",
        retention: str = "30 days",
    ):
        """
        设置日志系统

        Args:
            console_level: 控制台日志级别
            file_level: 文件日志级别
            enable_console: 是否启用控制台输出
            enable_file: 是否启用文件输出
            max_file_size: 单个日志文件最大大小
            rotation: 日志轮转间隔
            retention: 日志保留时间
        """

        # Clear default handlers
        logger.remove()

        # Select log format based on environment
        console_format = (
            self.dev_console_format
            if self.run_env == "dev"
            else self.prod_console_format
        )

        # Debug information (temporary)
        print(f"Current environment: {self.run_env}")
        print(
            f"Using log format: {'Development environment' if self.run_env == 'dev' else 'Production environment'}"
        )

        # Console handler
        if enable_console:
            logger.add(
                sys.stdout,
                format=console_format,
                level=console_level,
                colorize=True,
                backtrace=True,
                diagnose=True,
            )

        # File handler
        if enable_file:
            logger.add(
                str(self.log_file),
                format=self.file_format,
                level=file_level,
                rotation=rotation,
                retention=retention,
                compression="zip",
                backtrace=True,
                diagnose=True,
                encoding="utf-8",
            )

            # Error log file
            logger.add(
                str(self.error_file),
                format=self.file_format,
                level="ERROR",
                rotation=rotation,
                retention=retention,
                compression="zip",
                backtrace=True,
                diagnose=True,
                encoding="utf-8",
            )

    def get_logger(self, name: str = None):
        """
        Get logger

        Args:
            name: Logger name, if None returns default logger

        Returns:
            loguru logger instance
        """
        if name:
            return logger.bind(name=name)
        return logger


# Global logging configuration instance
log_config = LogConfig()


def init_logging(config: Optional[Dict[str, Any]] = None):
    """
    Initialize logging system

    Args:
        config: Logging configuration dictionary
    """
    if config is None:
        config = {}

    log_config.setup_logging(**config)


def get_logger(name: str = None):
    """
    Get logger

    Args:
        name: Logger name

    Returns:
        loguru logger instance
    """
    return log_config.get_logger(name)


# Predefined loggers
def get_app_logger():
    """Get application main logger"""
    return get_logger("ai_router")


def get_adapter_logger():
    """Get adapter logger"""
    return get_logger("ai_router.adapters")


def get_pool_logger():
    """Get adapter pool logger"""
    return get_logger("ai_router.pool")


def get_router_logger():
    """Get router logger"""
    return get_logger("ai_router.router")


def get_api_logger():
    """Get API logger"""
    return get_logger("ai_router.api")


def get_db_logger():
    """Get database logger"""
    return get_logger("ai_router.database")


def get_chat_logger():
    """Get chat logger"""
    return get_logger("ai_router.chat")


def get_health_logger():
    """Get health check logger"""
    return get_logger("ai_router.health")


def get_factory_logger():
    """Get adapter factory logger"""
    return get_logger("app.services.adapter_factory")


# Default configuration
DEFAULT_LOG_CONFIG = {
    "console_level": "INFO",
    "file_level": "DEBUG",
    "enable_console": True,
    "enable_file": True,
    "max_file_size": "10 MB",
    "rotation": "1 day",
    "retention": "30 days",
}


# Convenience functions
def log_info(message: str, logger_name: str = None):
    """Log information"""
    log = get_logger(logger_name)
    log.info(message)


def log_warning(message: str, logger_name: str = None):
    """Log warning"""
    log = get_logger(logger_name)
    log.warning(message)


def log_error(message: str, logger_name: str = None):
    """Log error"""
    log = get_logger(logger_name)
    log.error(message)


def log_debug(message: str, logger_name: str = None):
    """Log debug"""
    log = get_logger(logger_name)
    log.debug(message)


def log_success(message: str, logger_name: str = None):
    """Log success"""
    log = get_logger(logger_name)
    log.success(message)


def log_exception(message: str, logger_name: str = None):
    """Log exception"""
    log = get_logger(logger_name)
    log.exception(message)
