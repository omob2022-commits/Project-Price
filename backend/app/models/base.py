"""
Base model configuration for SQLAlchemy ORM.

Uses declarative mapping with async-compatible configuration.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    type_annotation_map = {
        datetime: DateTime(timezone=True),
    }

    def dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary.
        
        Useful for serialization and debugging.
        """
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }


def utc_now() -> datetime:
    """Return current UTC timestamp.
    
    Used as default for created_at/updated_at columns.
    """
    return datetime.now(timezone.utc)
