import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from loguru import logger
from config.settings import settings


class LogConfig:
    """日志配置类"""
    
    def __init__(self):
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # 日志文件路径
        self.log_file = self.log_dir / f"ai_router_{datetime.now().strftime('%Y%m%d')}.log"
        self.error_file = self.log_dir / f"ai_router_error_{datetime.now().strftime('%Y%m%d')}.log"
        
        # 获取环境变量
        self.run_env = settings.RUN_ENV
        
        # 开发环境日志格式（详细格式）
        self.dev_console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
            "<level>{message}</level>"
        )
        
        # 生产环境日志格式（简洁格式）
        self.prod_console_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<level>{message}</level>"
        )
        
        self.file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{name}:{function}:{line} | "
            "{message}"
        )
        
        # 日志级别
        self.console_level = "INFO"
        self.file_level = "DEBUG"
        self.error_level = "ERROR"
    
    def setup_logging(self, 
                     console_level: str = "INFO",
                     file_level: str = "DEBUG",
                     enable_console: bool = True,
                     enable_file: bool = True,
                     max_file_size: str = "10 MB",
                     rotation: str = "1 day",
                     retention: str = "30 days"):
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
        
        # 清除默认处理器
        logger.remove()
        
        # 根据环境选择日志格式
        console_format = self.dev_console_format if self.run_env == "dev" else self.prod_console_format
        
        # 调试信息（临时）
        print(f"当前环境: {self.run_env}")
        print(f"使用日志格式: {'开发环境' if self.run_env == 'dev' else '生产环境'}")
        
        # 控制台处理器
        if enable_console:
            logger.add(
                sys.stdout,
                format=console_format,
                level=console_level,
                colorize=True,
                backtrace=True,
                diagnose=True
            )
        
        # 文件处理器
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
                encoding="utf-8"
            )
            
            # 错误日志文件
            logger.add(
                str(self.error_file),
                format=self.file_format,
                level="ERROR",
                rotation=rotation,
                retention=retention,
                compression="zip",
                backtrace=True,
                diagnose=True,
                encoding="utf-8"
            )
    
    def get_logger(self, name: str = None):
        """
        获取日志器
        
        Args:
            name: 日志器名称，如果为None则返回默认日志器
        
        Returns:
            loguru logger实例
        """
        if name:
            return logger.bind(name=name)
        return logger


# 全局日志配置实例
log_config = LogConfig()


def init_logging(config: Optional[Dict[str, Any]] = None):
    """
    初始化日志系统
    
    Args:
        config: 日志配置字典
    """
    if config is None:
        config = {}
    
    log_config.setup_logging(**config)


def get_logger(name: str = None):
    """
    获取日志器
    
    Args:
        name: 日志器名称
    
    Returns:
        loguru logger实例
    """
    return log_config.get_logger(name)


# 预定义的日志器
def get_app_logger():
    """获取应用主日志器"""
    return get_logger("ai_router")


def get_adapter_logger():
    """获取适配器日志器"""
    return get_logger("ai_router.adapters")


def get_pool_logger():
    """获取适配器池日志器"""
    return get_logger("ai_router.pool")


def get_router_logger():
    """获取路由器日志器"""
    return get_logger("ai_router.router")


def get_api_logger():
    """获取API日志器"""
    return get_logger("ai_router.api")


def get_db_logger():
    """获取数据库日志器"""
    return get_logger("ai_router.database")


def get_chat_logger():
    """获取聊天日志器"""
    return get_logger("ai_router.chat")


def get_health_logger():
    """获取健康检查日志器"""
    return get_logger("ai_router.health")


def get_factory_logger():
    """获取适配器工厂日志器"""
    return get_logger("app.services.adapter_factory")


# 默认配置
DEFAULT_LOG_CONFIG = {
    "console_level": "INFO",
    "file_level": "DEBUG",
    "enable_console": True,
    "enable_file": True,
    "max_file_size": "10 MB",
    "rotation": "1 day",
    "retention": "30 days"
}


# 便捷函数
def log_info(message: str, logger_name: str = None):
    """记录信息日志"""
    log = get_logger(logger_name)
    log.info(message)


def log_warning(message: str, logger_name: str = None):
    """记录警告日志"""
    log = get_logger(logger_name)
    log.warning(message)


def log_error(message: str, logger_name: str = None):
    """记录错误日志"""
    log = get_logger(logger_name)
    log.error(message)


def log_debug(message: str, logger_name: str = None):
    """记录调试日志"""
    log = get_logger(logger_name)
    log.debug(message)


def log_success(message: str, logger_name: str = None):
    """记录成功日志"""
    log = get_logger(logger_name)
    log.success(message)


def log_exception(message: str, logger_name: str = None):
    """记录异常日志"""
    log = get_logger(logger_name)
    log.exception(message)
