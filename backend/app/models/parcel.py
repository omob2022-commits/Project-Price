"""
Parcel models for land parcels and user-saved valuations.

Parcels represent individual land plots with their computed valuations.
SavedParcel is a private user-parcel association for tracking searches.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from geoalchemy2 import Geometry
from sqlalchemy import (
    DECIMAL,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, utc_now

if TYPE_CHECKING:
    from app.models.user import User


class Parcel(Base):
    """Land parcel with computed valuation range.
    
    Attributes:
        id: Primary key
        geometry: PostGIS polygon geometry (WGS84 EPSG:4326)
        governorate: Governorate name (e.g., "Nablus")
        area_sqm: Parcel area in square meters
        
        # Geopolitical context
        oslo_classification: Area classification (A, B, C)
        
        # Zoning
        zoning_code: Master plan zoning designation
        zoning_description: Human-readable zoning type
        
        # Valuation (computed by engine)
        valuation_min_per_sqm: Lower bound of valuation range (₪/m²)
        valuation_max_per_sqm: Upper bound of valuation range (₪/m²)
        valuation_confidence: Statistical confidence level (e.g., 0.90)
        valuation_date: When the valuation was last computed
        comp_count: Number of comparable sales used
        degrees_of_freedom: N - p - 1 for regression model
        
        # Metadata
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "parcels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Geometry (PostGIS Polygon with SRID 4326 = WGS84)
    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="POLYGON", srid=4326),
        nullable=False,
    )
    
    governorate: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    area_sqm: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    
    # Geopolitical context
    oslo_classification: Mapped[str | None] = mapped_column(String(10), index=True)
    
    # Zoning
    zoning_code: Mapped[str | None] = mapped_column(String(50), index=True)
    zoning_description: Mapped[str | None] = mapped_column(String(255))
    
    # Valuation results
    valuation_min_per_sqm: Mapped[float | None] = mapped_column(Numeric(10, 2))
    valuation_max_per_sqm: Mapped[float | None] = mapped_column(Numeric(10, 2))
    valuation_confidence: Mapped[float | None] = mapped_column(Numeric(4, 3))
    valuation_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    comp_count: Mapped[int | None] = mapped_column(Integer)
    degrees_of_freedom: Mapped[int | None] = mapped_column(Integer)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    saved_by_users: Mapped[list["SavedParcel"]] = relationship(
        back_populates="parcel",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Parcel(id={self.id}, governorate='{self.governorate}', "
            f"area={self.area_sqm}m²)>"
        )


# Index for spatial queries (GiST)
Index(
    "idx_parcel_geometry_gist",
    Parcel.geometry,
    postgresql_using="gist",
)


class SavedParcel(Base):
    """User's saved parcel for tracking purchase intent.
    
    Privacy: This table is strictly private. No public activity feed.
    
    Attributes:
        id: Primary key
        user_id: Foreign key to User
        parcel_id: Foreign key to Parcel
        notes: Optional user notes about the parcel
        saved_at: When the user saved this parcel
    """

    __tablename__ = "saved_parcels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parcel_id: Mapped[int] = mapped_column(
        ForeignKey("parcels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    saved_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="saved_parcels")
    parcel: Mapped["Parcel"] = relationship(back_populates="saved_by_users")

    def __repr__(self) -> str:
        return f"<SavedParcel(user_id={self.user_id}, parcel_id={self.parcel_id})>"


# Unique constraint: user can only save a parcel once
Index(
    "idx_saved_parcel_user_parcel_unique",
    SavedParcel.user_id,
    SavedParcel.parcel_id,
    unique=True,
)
