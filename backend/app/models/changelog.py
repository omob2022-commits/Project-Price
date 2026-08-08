"""
Spatial data changelog model for tracking manual ETL imports.

Required per blueprint directive to maintain audit trail of all
spatial data updates, especially for manually-exported GeoMOLG data.
"""

from datetime import datetime

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, utc_now


class SpatialDataChangelog(Base):
    """Audit log for spatial data imports and updates.
    
    Because GeoMOLG and other spatial data sources require manual exports,
    this table provides an audit trail of what data was imported, when,
    and by whom.
    
    Attributes:
        id: Primary key
        table_name: Target table (e.g., "zoning_plans", "geopolitical_boundaries")
        operation: Type of operation (INSERT, UPDATE, DELETE, TRUNCATE)
        source_name: Data source identifier (e.g., "GeoMOLG", "OCHA HDX")
        source_version: Version/identifier of source dataset
        records_affected: Number of database records modified
        import_method: How data was imported (e.g., "manual_arcgis_export", "hdx_api")
        executed_by: Username/identifier of person who executed import
        notes: Additional context about the import
        executed_at: Timestamp of import execution
    """

    __tablename__ = "spatial_data_changelog"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    table_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Target table name",
    )
    
    operation: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="INSERT, UPDATE, DELETE, TRUNCATE",
    )
    
    source_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Data source identifier",
    )
    
    source_version: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Version/identifier of source dataset",
    )
    
    records_affected: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of records modified",
    )
    
    import_method: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="How data was imported (e.g., manual_arcgis_export)",
    )
    
    executed_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Username/identifier of person who executed import",
    )
    
    notes: Mapped[str | None] = mapped_column(
        Text,
        comment="Additional context about the import",
    )
    
    executed_at: Mapped[datetime] = mapped_column(
        default=utc_now,
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<SpatialDataChangelog(id={self.id}, "
            f"table='{self.table_name}', "
            f"operation='{self.operation}', "
            f"records={self.records_affected})>"
        )
