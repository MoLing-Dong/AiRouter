"""
查询构建器
提供复杂查询的构建方法
"""

from sqlmodel import select
from .sqlmodel_models import (
    LLMModel,
    LLMProvider,
    LLMModelProvider,
    HealthStatus,
)


class QueryBuilder:
    """查询构建器 - 提供复杂查询的构建方法"""

    @staticmethod
    def get_models_with_healthy_providers():
        """获取有健康提供商的模型"""
        return (
            select(LLMModel)
            .join(LLMModelProvider)
            .where(
                LLMModel.is_enabled == True,
                LLMModelProvider.is_enabled == True,
                LLMModelProvider.health_status == HealthStatus.healthy,
            )
            .distinct()
        )

    @staticmethod
    def get_top_performing_providers(limit: int = 10):
        """获取性能最佳的提供商"""
        return (
            select(LLMProvider, LLMModelProvider.overall_score.label("avg_score"))
            .join(LLMModelProvider)
            .where(LLMProvider.is_enabled == True, LLMModelProvider.is_enabled == True)
            .group_by(LLMProvider.id)
            .order_by(LLMModelProvider.overall_score.desc())
            .limit(limit)
        )

    @staticmethod
    def get_models_by_performance_threshold(min_score: float = 0.8):
        """获取性能超过阈值的模型"""
        return (
            select(LLMModel)
            .join(LLMModelProvider)
            .where(
                LLMModel.is_enabled == True, LLMModelProvider.overall_score >= min_score
            )
            .distinct()
        )
