"""
Base services package
提供基础的服务抽象和事务管理
"""

from .transaction_manager import BaseTransactionManager, DatabaseTransactionManager
from .repository_base import BaseRepository

__all__ = ["BaseTransactionManager", "DatabaseTransactionManager", "BaseRepository"]
