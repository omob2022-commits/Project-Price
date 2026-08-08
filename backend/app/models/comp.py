"""
Comparable sales (comps) model for valuation engine.

Stores verified market transactions used as training data for the
hedonic regression model.
"""

from datetime import date, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Date, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class Comp(Base):
    """Comparable sale (comp) record for valuation modeling.
    
    Each comp represents a verified land transaction used as training
    data for the hedonic regression model. Comps must be spatially
    referenced and include all relevant pricing factors.
    
    Attributes:
        id: Primary key
        geometry: PostGIS point geometry (centroid of parcel, WGS84 EPSG:4326)
        governorate: Governorate name (e.g., "Nablus")
        locality: City/town/village name
        
        # Transaction details
        sale_date: Date of transaction
        price_ils: Sale price in Israeli Shekels (₪)
        area_sqm: Parcel area in square meters
        price_per_sqm: Computed ₪/m² (denormalized for query efficiency)
        
        # Location factors
        oslo_classification: Area classification (A, B, C) at time of sale
        zoning_code: Zoning designation at time of sale
        distance_to_road_m: Distance to nearest paved road (meters)
        distance_to_city_center_m: Distance to governorate capital (meters)
        
        # Property characteristics
        has_water_access: Water infrastructure availability
        has_electricity_access: Electricity infrastructure availability
        slope_category: Terrain classification (flat, moderate, steep)
        
        # Data provenance
        source: Data source (e.g., "Real Estate Agent", "Court Records")
        source_confidence: Confidence level (1-5 scale, 5 = highest)
        verified_by: Who verified this transaction
        verification_date: When verification occurred
        
        # Metadata
        notes: Additional contextual information
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    __tablename__ = "comps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Geometry (PostGIS Point with SRID 4326 = WGS84)
    geometry: Mapped[str] = mapped_column(
        Geometry(geometry_type="POINT", srid=4326),
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
    )
    
    # Transaction details
    sale_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    price_ils: Mapped[float] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Sale price in Israeli Shekels (₪)",
    )
    area_sqm: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    price_per_sqm: Mapped[float] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        index=True,
        comment="Computed ₪/m² (denormalized)",
    )
    
    # Location factors
    oslo_classification: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True,
    )
    zoning_code: Mapped[str | None] = mapped_column(String(50), index=True)
    distance_to_road_m: Mapped[float | None] = mapped_column(Numeric(10, 2))
    distance_to_city_center_m: Mapped[float | None] = mapped_column(Numeric(10, 2))
    
    # Property characteristics
    has_water_access: Mapped[bool | None] = mapped_column()
    has_electricity_access: Mapped[bool | None] = mapped_column()
    slope_category: Mapped[str | None] = mapped_column(
        String(20),
        comment="flat, moderate, steep",
    )
    
    # Data provenance
    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Data source identifier",
    )
    source_confidence: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Confidence level 1-5 (5=highest)",
    )
    verified_by: Mapped[str | None] = mapped_column(String(255))
    verification_date: Mapped[date | None] = mapped_column(Date)
    
    # Metadata
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<Comp(id={self.id}, locality='{self.locality}', "
            f"price={self.price_per_sqm}₪/m², date={self.sale_date})>"
        )


# GiST spatial index for efficient ST_DWithin distance queries
Index(
    "idx_comp_geometry_gist",
    Comp.geometry,
    postgresql_using="gist",
)

# Composite index for filtering by governorate + sale date
Index(
    "idx_comp_gov_date",
    Comp.governorate,
    Comp.sale_date.desc(),
)

# Index for Oslo classification filtering
Index(
    "idx_comp_oslo",
    Comp.oslo_classification,
)

# Index for price range queries
Index(
    "idx_comp_price_per_sqm",
    Comp.price_per_sqm,
)
