"""
Health Check Service for managing asynchronous health checks
"""

import asyncio
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from ..models.llm_model_provider import HealthStatusEnum
from .database_service import DatabaseService
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class HealthCheckService:
    """Health check service for managing health status synchronization"""

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def sync_adapter_health_to_database(
        self,
        model_id: int,
        provider_id: int,
        health_status: str,
        response_time: float = None,
        success: bool = None,
        error_message: str = None,
    ) -> bool:
        """Synchronize adapter health status to database

        Args:
            model_id: Model ID
            provider_id: Provider ID
            health_status: Health status (healthy, degraded, unhealthy)
            response_time: Response time in seconds
            success: Whether the request was successful
            error_message: Error message if any

        Returns:
            bool: True if sync successful, False otherwise
        """
        try:
            # Map adapter health status to database health status
            db_health_status = self._map_health_status(health_status)

            # Update health status in database
            result = self.db_service.update_model_provider_health_status(
                model_id=model_id,
                provider_id=provider_id,
                health_status=db_health_status,
                response_time=response_time,
                success=success,
            )

            if result:
                logger.info(
                    f"✅ Health status synced to database: Model {model_id}, "
                    f"Provider {provider_id}, Status: {db_health_status}"
                )
            else:
                logger.warning(
                    f"⚠️ Failed to sync health status to database: Model {model_id}, "
                    f"Provider {provider_id}"
                )

            return result

        except Exception as e:
            logger.error(f"❌ Error syncing health status to database: {e}")
            return False

    def sync_adapter_metrics_to_database(
        self,
        model_id: int,
        provider_id: int,
        response_time: float,
        success: bool,
        tokens_used: int = 0,
        cost: float = 0.0,
    ) -> bool:
        """Synchronize adapter metrics to database

        Args:
            model_id: Model ID
            provider_id: Provider ID
            response_time: Response time in seconds
            success: Whether the request was successful
            tokens_used: Number of tokens used
            cost: Cost of the request

        Returns:
            bool: True if sync successful, False otherwise
        """
        try:
            result = self.db_service.update_model_provider_metrics(
                model_id=model_id,
                provider_id=provider_id,
                response_time=response_time,
                success=success,
                tokens_used=tokens_used,
                cost=cost,
            )

            if result:
                logger.debug(
                    f"✅ Metrics synced to database: Model {model_id}, "
                    f"Provider {provider_id}, Response time: {response_time}s, "
                    f"Success: {success}"
                )
            else:
                logger.warning(
                    f"⚠️ Failed to sync metrics to database: Model {model_id}, "
                    f"Provider {provider_id}"
                )

            return result

        except Exception as e:
            logger.error(f"❌ Error syncing metrics to database: {e}")
            return False

    def update_failure_count(
        self, model_id: int, provider_id: int, increment: bool = True
    ) -> bool:
        """Update failure count in database

        Args:
            model_id: Model ID
            provider_id: Provider ID
            increment: Whether to increment or reset failure count

        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            if increment:
                result = self.db_service.increment_failure_count(model_id, provider_id)
            else:
                result = self.db_service.reset_failure_count(model_id, provider_id)

            if result:
                action = "incremented" if increment else "reset"
                logger.info(
                    f"✅ Failure count {action}: Model {model_id}, Provider {provider_id}"
                )
            else:
                action = "increment" if increment else "reset"
                logger.warning(
                    f"⚠️ Failed to {action} failure count: Model {model_id}, "
                    f"Provider {provider_id}"
                )

            return result

        except Exception as e:
            logger.error(f"❌ Error updating failure count: {e}")
            return False

    def get_health_summary(self, model_id: int, provider_id: int) -> Dict[str, Any]:
        """Get health summary for a model-provider combination

        Args:
            model_id: Model ID
            provider_id: Provider ID

        Returns:
            Dict containing health summary
        """
        try:
            stats = self.db_service.get_model_provider_stats(model_id, provider_id)
            if not stats:
                return {}

            return {
                "health_status": stats.get("health_status"),
                "response_time_avg": stats.get("response_time_avg"),
                "success_rate": stats.get("success_rate"),
                "total_requests": stats.get("total_requests"),
                "successful_requests": stats.get("successful_requests"),
                "failed_requests": stats.get("failed_requests"),
                "failure_count": stats.get("failure_count"),
                "last_health_check": stats.get("last_health_check"),
                "last_failure_time": stats.get("last_failure_time"),
                "overall_score": stats.get("overall_score"),
            }

        except Exception as e:
            logger.error(f"❌ Error getting health summary: {e}")
            return {}

    def _map_health_status(self, adapter_status: str) -> str:
        """Map adapter health status to database health status

        Args:
            adapter_status: Health status from adapter

        Returns:
            Database health status
        """
        status_mapping = {
            "healthy": HealthStatusEnum.HEALTHY.value,
            "unhealthy": HealthStatusEnum.UNHEALTHY.value,
            "degraded": HealthStatusEnum.DEGRADED.value,
        }

        return status_mapping.get(
            adapter_status.lower(), HealthStatusEnum.UNHEALTHY.value
        )

    def batch_sync_health_status(
        self, health_updates: List[Dict[str, Any]]
    ) -> Dict[str, bool]:
        """Batch sync health status updates

        Args:
            health_updates: List of health update dictionaries

        Returns:
            Dict mapping update ID to success status
        """
        results = {}

        for update in health_updates:
            update_id = f"{update.get('model_id')}_{update.get('provider_id')}"

            success = self.sync_adapter_health_to_database(
                model_id=update.get("model_id"),
                provider_id=update.get("provider_id"),
                health_status=update.get("health_status"),
                response_time=update.get("response_time"),
                success=update.get("success"),
                error_message=update.get("error_message"),
            )

            results[update_id] = success

        return results
