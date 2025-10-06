"""
Capability Domain Services
能力领域服务模块

职责：
- 能力的定义和管理
- 模型能力的关联管理
- 能力的增删改查

服务列表：
- CapabilityService: 能力管理服务
"""

from .capability_service import CapabilityService, capability_service

__all__ = [
    "CapabilityService",
    "capability_service",
]
