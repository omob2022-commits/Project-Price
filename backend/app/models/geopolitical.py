"""
Geopolitical boundary model for Oslo Accords classifications (Areas A, B, C).

Data sourced from OCHA Humanitarian Data Exchange (HDX).
"""

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class GeopoliticalBoundary(Base):
    """Oslo Accords area classification boundaries.
    
    Represents the geopolitical divisions in the West Bank:
    - Area A: Full Palestinian civil and security control
    - Area B: Palestinian civil control, Israeli security control
    - Area C: Full Israeli civil and security control
    
    These classifications have significant impact on land values and
    development restrictions.
    
    Attributes:
        id: Primary key
        geometry: PostGIS multipolygon geometry (WGS84 EPSG:4326)
        classification: Area type (A, B, or C)
        governorate: Governorate name (e.g., "Nablus")
        
        # Data provenance (mandatory)
        source_version: Version/identifier of the source dataset
        effective_date: Date when this boundary became effective
        
        # Metadata
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "geopolitical_boundaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Geometry (PostGIS MultiPolygon with SRID 4326 = WGS84)
    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
    )
    
    classification: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
        comment="Oslo classification: A, B, or C",
    )
    
    governorate: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    
    # Data provenance (mandatory per blueprint directive)
    source_version: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="OCHA HDX dataset version/identifier",
    )
    
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date when boundary became effective",
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<GeopoliticalBoundary(id={self.id}, "
            f"classification='{self.classification}', "
            f"governorate='{self.governorate}')>"
        )


# GiST spatial index for efficient ST_Intersects queries
Index(
    "idx_geopolitical_geometry_gist",
    GeopoliticalBoundary.geometry,
    postgresql_using="gist",
)

# Composite index for filtering by governorate + classification
Index(
    "idx_geopolitical_gov_class",
    GeopoliticalBoundary.governorate,
    GeopoliticalBoundary.classification,
)
