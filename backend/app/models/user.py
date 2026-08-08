"""
User model for authentication and profile management.

Privacy-by-default: User data and saved parcels are strictly private.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.parcel import SavedParcel


class User(Base):
    """User account with authentication credentials.
    
    Attributes:
        id: Primary key
        email: Unique email address (used for login)
        hashed_password: Bcrypt password hash
        full_name: User's display name
        is_active: Account status (for soft deletion/suspension)
        created_at: Account creation timestamp
        updated_at: Last profile update timestamp
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    saved_parcels: Mapped[list["SavedParcel"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"
