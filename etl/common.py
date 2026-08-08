"""
Common utilities for ETL scripts.

Provides shared functionality for:
- CRS validation and reprojection
- Database connections
- Changelog logging
- Progress tracking
"""

import os
import sys
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Optional

import geopandas as gpd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv(Path(__file__).parent.parent / "backend" / ".env")

# Target CRS: WGS84 (EPSG:4326) - required by blueprint
TARGET_CRS = "EPSG:4326"


def get_db_engine(sync: bool = True):
    """Get SQLAlchemy engine for database operations.
    
    Args:
        sync: If True, use synchronous psycopg2 driver (for ETL).
              If False, use async asyncpg driver.
    
    Returns:
        SQLAlchemy Engine instance
    """
    if sync:
        db_url = os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql://landval:changeme@localhost:5432/landval_db"
        )
    else:
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://landval:changeme@localhost:5432/landval_db"
        )
    
    return create_engine(db_url, echo=False)


def get_db_session():
    """Get SQLAlchemy session for database operations.
    
    Returns:
        SQLAlchemy Session instance
    """
    engine = get_db_engine(sync=True)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def validate_and_reproject_gdf(
    gdf: gpd.GeoDataFrame,
    source_name: str,
    assert_crs: bool = True
) -> gpd.GeoDataFrame:
    """Validate and reproject GeoDataFrame to target CRS.
    
    Per blueprint directive: "The GeoPandas ETL script must contain hard 
    assertions to check and reproject all incoming data to one consistent 
    Coordinate Reference System (e.g., EPSG:4326) before PostGIS insertion."
    
    Args:
        gdf: Input GeoDataFrame
        source_name: Name of data source (for error messages)
        assert_crs: If True, assert that CRS is defined (fail if not)
    
    Returns:
        GeoDataFrame reprojected to TARGET_CRS
    
    Raises:
        AssertionError: If CRS is not defined and assert_crs=True
    """
    # Hard assertion: CRS must be defined
    if assert_crs:
        assert gdf.crs is not None, (
            f"CRS assertion failed for {source_name}: "
            f"Input data has no CRS defined. All spatial data must have a "
            f"defined coordinate reference system."
        )
    
    # Check if reprojection is needed
    if gdf.crs is None:
        print(f"⚠️  WARNING: {source_name} has no CRS, assuming {TARGET_CRS}")
        gdf = gdf.set_crs(TARGET_CRS)
    elif gdf.crs != TARGET_CRS:
        print(f"🔄 Reprojecting {source_name} from {gdf.crs} to {TARGET_CRS}")
        gdf = gdf.to_crs(TARGET_CRS)
    else:
        print(f"✓ {source_name} already in {TARGET_CRS}")
    
    return gdf


def log_spatial_data_change(
    session,
    table_name: str,
    operation: str,
    source_name: str,
    source_version: str,
    records_affected: int,
    import_method: str,
    executed_by: str,
    notes: Optional[str] = None
) -> None:
    """Log ETL operation to spatial_data_changelog table.
    
    Per blueprint directive: "A spatial_data_changelog table must be 
    maintained alongside the source_version column to track all manual imports."
    
    Args:
        session: SQLAlchemy session
        table_name: Target table name
        operation: Operation type (INSERT, UPDATE, DELETE, TRUNCATE)
        source_name: Data source identifier
        source_version: Version/identifier of source dataset
        records_affected: Number of records modified
        import_method: How data was imported
        executed_by: Username/identifier of person who executed import
        notes: Optional additional context
    """
    insert_sql = text("""
        INSERT INTO spatial_data_changelog (
            table_name,
            operation,
            source_name,
            source_version,
            records_affected,
            import_method,
            executed_by,
            notes,
            executed_at
        ) VALUES (
            :table_name,
            :operation,
            :source_name,
            :source_version,
            :records_affected,
            :import_method,
            :executed_by,
            :notes,
            :executed_at
        )
    """)
    
    session.execute(insert_sql, {
        "table_name": table_name,
        "operation": operation,
        "source_name": source_name,
        "source_version": source_version,
        "records_affected": records_affected,
        "import_method": import_method,
        "executed_by": executed_by,
        "notes": notes,
        "executed_at": datetime.now(timezone.utc)
    })
    session.commit()
    
    print(f"📝 Logged to spatial_data_changelog: {table_name} ({records_affected} records)")


def validate_geometries(gdf: gpd.GeoDataFrame, source_name: str) -> gpd.GeoDataFrame:
    """Validate and fix invalid geometries.
    
    Args:
        gdf: Input GeoDataFrame
        source_name: Name of data source (for logging)
    
    Returns:
        GeoDataFrame with valid geometries
    """
    invalid_count = (~gdf.geometry.is_valid).sum()
    
    if invalid_count > 0:
        print(f"⚠️  Found {invalid_count} invalid geometries in {source_name}")
        print(f"🔧 Attempting to fix with buffer(0)...")
        gdf["geometry"] = gdf.geometry.buffer(0)
        
        # Check again
        still_invalid = (~gdf.geometry.is_valid).sum()
        if still_invalid > 0:
            print(f"❌ ERROR: {still_invalid} geometries still invalid after repair")
            print("   Removing invalid geometries...")
            gdf = gdf[gdf.geometry.is_valid].copy()
        else:
            print(f"✓ All geometries fixed successfully")
    else:
        print(f"✓ All geometries valid in {source_name}")
    
    return gdf


def get_nablus_filter() -> str:
    """Get governorate filter for Phase 1 (Nablus only).
    
    Returns:
        Governorate name for filtering
    """
    return os.getenv("ACTIVE_GOVERNORATE", "Nablus")


def confirm_action(message: str) -> bool:
    """Prompt user for confirmation before destructive operations.
    
    Args:
        message: Confirmation message to display
    
    Returns:
        True if user confirms, False otherwise
    """
    response = input(f"{message} (yes/no): ").strip().lower()
    return response in ("yes", "y")
