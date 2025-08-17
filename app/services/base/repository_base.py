"""
Base Repository Pattern
提供通用的数据访问抽象层
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any, Type
from sqlalchemy.orm import Session
from .transaction_manager import DatabaseTransactionManager

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Base repository with common CRUD operations"""

    def __init__(
        self, transaction_manager: DatabaseTransactionManager, entity_class: Type[T]
    ):
        self.tx_manager = transaction_manager
        self.entity_class = entity_class

    def get_by_id(self, entity_id: int) -> Optional[T]:
        """Get entity by ID"""

        def operation(session: Session) -> Optional[T]:
            return (
                session.query(self.entity_class)
                .filter(self.entity_class.id == entity_id)
                .first()
            )

        return self.tx_manager.execute_in_transaction(
            operation, f"Get {self.entity_class.__name__} by ID {entity_id}"
        )

    def get_all(
        self, filters: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None
    ) -> List[T]:
        """Get all entities with optional filtering and ordering"""

        def operation(session: Session) -> List[T]:
            query = session.query(self.entity_class)

            if filters:
                for key, value in filters.items():
                    if hasattr(self.entity_class, key):
                        query = query.filter(getattr(self.entity_class, key) == value)

            if order_by:
                if hasattr(self.entity_class, order_by):
                    query = query.order_by(getattr(self.entity_class, order_by))

            return query.all()

        return self.tx_manager.execute_in_transaction(
            operation, f"Get all {self.entity_class.__name__} with filters {filters}"
        )

    def create(self, entity_data: Dict[str, Any]) -> T:
        """Create new entity"""

        def operation(session: Session) -> T:
            entity = self.entity_class(**entity_data)
            session.add(entity)
            session.flush()  # Get ID without committing
            session.refresh(entity)
            return entity

        return self.tx_manager.execute_in_transaction(
            operation, f"Create {self.entity_class.__name__}"
        )

    def update(self, entity_id: int, update_data: Dict[str, Any]) -> Optional[T]:
        """Update existing entity"""

        def operation(session: Session) -> Optional[T]:
            entity = (
                session.query(self.entity_class)
                .filter(self.entity_class.id == entity_id)
                .first()
            )
            if not entity:
                return None

            for key, value in update_data.items():
                if hasattr(entity, key):
                    setattr(entity, key, value)

            session.flush()
            session.refresh(entity)
            return entity

        return self.tx_manager.execute_in_transaction(
            operation, f"Update {self.entity_class.__name__} with ID {entity_id}"
        )

    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID"""

        def operation(session: Session) -> bool:
            entity = (
                session.query(self.entity_class)
                .filter(self.entity_class.id == entity_id)
                .first()
            )
            if not entity:
                return False

            session.delete(entity)
            return True

        return self.tx_manager.execute_in_transaction(
            operation, f"Delete {self.entity_class.__name__} with ID {entity_id}"
        )

    def exists(self, entity_id: int) -> bool:
        """Check if entity exists"""

        def operation(session: Session) -> bool:
            return (
                session.query(self.entity_class)
                .filter(self.entity_class.id == entity_id)
                .first()
                is not None
            )

        return self.tx_manager.execute_in_transaction(
            operation,
            f"Check existence of {self.entity_class.__name__} with ID {entity_id}",
        )

    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities with optional filtering"""

        def operation(session: Session) -> int:
            query = session.query(self.entity_class)

            if filters:
                for key, value in filters.items():
                    if hasattr(self.entity_class, key):
                        query = query.filter(getattr(self.entity_class, key) == value)

            return query.count()

        return self.tx_manager.execute_in_transaction(
            operation, f"Count {self.entity_class.__name__} with filters {filters}"
        )

    @abstractmethod
    def validate_entity(self, entity_data: Dict[str, Any]) -> None:
        """Validate entity data before creation/update"""
        pass

    def create_with_validation(self, entity_data: Dict[str, Any]) -> T:
        """Create entity with validation"""
        self.validate_entity(entity_data)
        return self.create(entity_data)

    def update_with_validation(
        self, entity_id: int, update_data: Dict[str, Any]
    ) -> Optional[T]:
        """Update entity with validation"""
        self.validate_entity(update_data)
        return self.update(entity_id, update_data)
