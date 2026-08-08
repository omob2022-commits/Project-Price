"""
Zoning plan model for Palestinian master plans (المخططات الهيكلية).

Data sourced from GeoMOLG with manual ArcGIS exports.
"""

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class ZoningPlan(Base):
    """Master plan zoning designations from GeoMOLG.
    
    Represents approved zoning classifications that define permitted
    land uses, building heights, and development density.
    
    Because GeoMOLG requires manual ArcGIS exports, this table must be
    paired with a detailed ETL runbook (geomolg_etl_runbook.md).
    
    Attributes:
        id: Primary key
        geometry: PostGIS multipolygon geometry (WGS84 EPSG:4326)
        governorate: Governorate name (e.g., "Nablus")
        locality: Specific city/town/village name
        zoning_code: Official zoning code (e.g., "R1", "C2", "I")
        zoning_description: Human-readable description (e.g., "Residential Low Density")
        max_building_height: Maximum permitted building height (meters)
        max_floor_area_ratio: Maximum FAR (floor area / lot area)
        
        # Data provenance (mandatory)
        source_version: GeoMOLG export identifier/date
        effective_date: Date when zoning became effective
        plan_approval_date: Date when master plan was officially approved
        
        # Metadata
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "zoning_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Geometry (PostGIS MultiPolygon with SRID 4326 = WGS84)
    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=4326),
        nullable=False,
    )
    
    governorate: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    
    locality: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="City/town/village name",
    )
    
    zoning_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Official zoning designation code",
    )
    
    zoning_description: Mapped[str | None] = mapped_column(
        Text,
        comment="Human-readable zoning description",
    )
    
    max_building_height: Mapped[float | None] = mapped_column(
        Integer,
        comment="Maximum building height in meters",
    )
    
    max_floor_area_ratio: Mapped[float | None] = mapped_column(
        String(10),
        comment="Maximum FAR (e.g., 1.5, 2.0)",
    )
    
    # Data provenance (mandatory per blueprint directive)
    source_version: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="GeoMOLG export identifier/timestamp",
    )
    
    effective_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        comment="Date when zoning became effective",
    )
    
    plan_approval_date: Mapped[date | None] = mapped_column(
        Date,
        comment="Master plan official approval date",
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
            f"<ZoningPlan(id={self.id}, "
            f"locality='{self.locality}', "
            f"code='{self.zoning_code}')>"
        )


# GiST spatial index for efficient ST_Intersects queries
Index(
    "idx_zoning_geometry_gist",
    ZoningPlan.geometry,
    postgresql_using="gist",
)

# Composite index for filtering by governorate + locality
Index(
    "idx_zoning_gov_locality",
    ZoningPlan.governorate,
    ZoningPlan.locality,
)

# Index for zoning code lookups
Index(
    "idx_zoning_code",
    ZoningPlan.zoning_code,
)
