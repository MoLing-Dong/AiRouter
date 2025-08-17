"""
Transaction Manager for Database Operations
提供统一的事务管理接口，确保事务的原子性、一致性和隔离性
"""

from contextlib import contextmanager
from typing import Optional, Any, Callable
from datetime import datetime
from sqlalchemy.orm import Session
from app.utils.logging_config import get_factory_logger

logger = get_factory_logger()


class TransactionManager:
    """Database transaction manager"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    @contextmanager
    def transaction(self, description: str = "Database operation"):
        """
        事务上下文管理器

        Args:
            description: 事务描述，用于日志记录

        Yields:
            Session: 数据库会话对象

        Raises:
            Exception: 任何在事务中发生的异常
        """
        session: Optional[Session] = None
        start_time = None
        try:
            session = self.session_factory()
            start_time = datetime.now()
            logger.info(f"🚀 Starting transaction: {description}")
            logger.debug(f"   📍 Session ID: {id(session)}")
            logger.debug(f"   ⏰ Start time: {start_time}")

            yield session

            # 如果没有异常，提交事务
            commit_start = datetime.now()
            session.commit()
            commit_duration = (datetime.now() - commit_start).total_seconds() * 1000
            total_duration = (datetime.now() - start_time).total_seconds() * 1000

            logger.info(f"✅ Transaction committed successfully: {description}")
            logger.debug(f"   📍 Session ID: {id(session)}")
            logger.debug(f"   ⏱️  Total duration: {total_duration:.2f}ms")
            logger.debug(f"   ⚡ Commit duration: {commit_duration:.2f}ms")

        except Exception as e:
            # 发生异常时回滚事务
            if session:
                rollback_start = datetime.now()
                session.rollback()
                rollback_duration = (
                    datetime.now() - rollback_start
                ).total_seconds() * 1000
                total_duration = (
                    (datetime.now() - start_time).total_seconds() * 1000
                    if start_time
                    else 0
                )

                logger.error(f"❌ Transaction rolled back due to error: {description}")
                logger.error(f"   📍 Session ID: {id(session)}")
                logger.error(f"   🚨 Error type: {type(e).__name__}")
                logger.error(f"   💬 Error message: {str(e)}")
                logger.error(
                    f"   ⏱️  Total duration before rollback: {total_duration:.2f}ms"
                )
                logger.error(f"   🔄 Rollback duration: {rollback_duration:.2f}ms")

                # 记录详细的错误堆栈
                import traceback

                logger.error(f"   📚 Stack trace:\n{traceback.format_exc()}")

            # 重新抛出异常
            raise

        finally:
            # 总是关闭会话
            if session:
                close_start = datetime.now()
                session.close()
                close_duration = (datetime.now() - close_start).total_seconds() * 1000
                total_duration = (
                    (datetime.now() - start_time).total_seconds() * 1000
                    if start_time
                    else 0
                )

                logger.debug(f"🔒 Session closed: {description}")
                logger.debug(f"   📍 Session ID: {id(session)}")
                logger.debug(f"   ⏱️  Total duration: {total_duration:.2f}ms")
                logger.debug(f"   🔒 Close duration: {close_duration:.2f}ms")

    def execute_in_transaction(
        self,
        operation: Callable[[Session], Any],
        description: str = "Database operation",
    ) -> Any:
        """
        在事务中执行操作

        Args:
            operation: 要执行的操作函数，接受Session参数
            description: 事务描述

        Returns:
            操作的结果

        Raises:
            Exception: 操作失败时抛出的异常
        """
        with self.transaction(description) as session:
            return operation(session)

    def execute_with_retry(
        self,
        operation: Callable[[Session], Any],
        max_retries: int = 3,
        description: str = "Database operation",
    ) -> Any:
        """
        带重试机制的事务执行

        Args:
            operation: 要执行的操作函数
            max_retries: 最大重试次数
            description: 事务描述

        Returns:
            操作的结果

        Raises:
            Exception: 所有重试都失败后抛出的异常
        """
        last_exception = None
        start_time = datetime.now()

        logger.info(
            f"🔄 Starting retry operation: {description} (max retries: {max_retries})"
        )
        logger.debug(f"   ⏰ Start time: {start_time}")

        for attempt in range(max_retries):
            attempt_start = datetime.now()
            try:
                logger.info(
                    f"🔄 Attempt {attempt + 1}/{max_retries} for: {description}"
                )

                result = self.execute_in_transaction(
                    operation, f"{description} (attempt {attempt + 1})"
                )

                attempt_duration = (
                    datetime.now() - attempt_start
                ).total_seconds() * 1000
                total_duration = (datetime.now() - start_time).total_seconds() * 1000

                logger.info(
                    f"✅ Operation succeeded on attempt {attempt + 1}: {description}"
                )
                logger.debug(f"   ⏱️  Attempt duration: {attempt_duration:.2f}ms")
                logger.debug(f"   ⏱️  Total duration: {total_duration:.2f}ms")

                return result

            except Exception as e:
                last_exception = e
                attempt_duration = (
                    datetime.now() - attempt_start
                ).total_seconds() * 1000

                logger.warning(
                    f"⚠️ Attempt {attempt + 1}/{max_retries} failed for {description}"
                )
                logger.warning(f"   🚨 Error type: {type(e).__name__}")
                logger.warning(f"   💬 Error message: {str(e)}")
                logger.warning(f"   ⏱️  Attempt duration: {attempt_duration:.2f}ms")

                if attempt < max_retries - 1:
                    # 等待一段时间后重试（指数退避）
                    import time

                    wait_time = 2**attempt
                    logger.info(f"   ⏳ Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"   ❌ No more retries available")

        # 所有重试都失败了
        total_duration = (datetime.now() - start_time).total_seconds() * 1000
        logger.error(f"❌ All {max_retries} attempts failed for {description}")
        logger.error(f"   🚨 Final error type: {type(last_exception).__name__}")
        logger.error(f"   💬 Final error message: {str(last_exception)}")
        logger.error(f"   ⏱️  Total time spent: {total_duration:.2f}ms")

        raise last_exception


class DatabaseTransactionManager(TransactionManager):
    """Database-specific transaction manager with additional features"""

    def __init__(self, session_factory):
        super().__init__(session_factory)

    def validate_entity_exists(
        self,
        session: Session,
        entity_class,
        entity_id: int,
        entity_name: str = "Entity",
    ) -> Any:
        """
        验证实体是否存在

        Args:
            session: 数据库会话
            entity_class: 实体类
            entity_id: 实体ID
            entity_name: 实体名称（用于错误消息）

        Returns:
            实体对象

        Raises:
            ValueError: 实体不存在时抛出
        """
        logger.debug(f"🔍 Validating {entity_name} existence: ID {entity_id}")

        entity = (
            session.query(entity_class).filter(entity_class.id == entity_id).first()
        )

        if not entity:
            logger.error(
                f"❌ {entity_name} validation failed: ID {entity_id} does not exist"
            )
            raise ValueError(f"{entity_name} with ID {entity_id} does not exist")

        logger.debug(f"✅ {entity_name} validation passed: ID {entity_id} exists")
        return entity

    def validate_entity_enabled(self, entity, entity_name: str = "Entity") -> None:
        """
        验证实体是否启用

        Args:
            entity: 实体对象
            entity_name: 实体名称（用于错误消息）

        Raises:
            ValueError: 实体未启用时抛出
        """
        logger.debug(f"🔍 Validating {entity_name} enabled status: ID {entity.id}")

        if hasattr(entity, "is_enabled") and not entity.is_enabled:
            logger.error(
                f"❌ {entity_name} validation failed: ID {entity.id} is disabled"
            )
            raise ValueError(f"{entity_name} with ID {entity.id} is disabled")

        logger.debug(
            f"✅ {entity_name} enabled status validation passed: ID {entity.id}"
        )

    def check_unique_constraint(
        self, session: Session, entity_class, filters: dict, entity_name: str = "Entity"
    ) -> None:
        """
        检查唯一性约束

        Args:
            session: 数据库会话
            entity_class: 实体类
            filters: 过滤条件
            entity_name: 实体名称（用于错误消息）

        Raises:
            ValueError: 违反唯一性约束时抛出
        """
        filter_str = ", ".join([f"{k}={v}" for k, v in filters.items()])
        logger.debug(f"🔍 Checking unique constraint for {entity_name}: {filter_str}")

        existing = session.query(entity_class).filter_by(**filters).first()
        if existing:
            logger.error(
                f"❌ Unique constraint violation: {entity_name} with {filter_str} already exists"
            )
            raise ValueError(f"{entity_name} with {filter_str} already exists")

        logger.debug(
            f"✅ Unique constraint check passed for {entity_name}: {filter_str}"
        )
