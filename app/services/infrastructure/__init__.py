"""
Infrastructure Services Module
基础设施服务模块

职责：
- 服务生命周期管理
- 依赖注入和服务工厂
- 跨服务协调和编排
- 框架级别的支持功能

服务列表：
- ServiceFactory: 服务工厂，负责服务实例化和依赖注入
- ServiceManager: 服务管理器，负责服务协调和统一访问
"""

from .service_factory import ServiceFactory
from .service_manager import ServiceManager

__all__ = [
    "ServiceFactory",
    "ServiceManager",
]
