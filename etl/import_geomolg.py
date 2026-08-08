#!/usr/bin/env python3
"""
GeoMOLG Master Plans ETL Script

Imports Palestinian master plan zoning data from GeoMOLG 
(المخططات الهيكلية المصدقة) into the zoning_plans table.

Data Source: GeoMOLG (https://geomolg.pna.ps/)
Export Process: See geomolg_etl_runbook.md for detailed export instructions

Usage:
    python etl/import_geomolg.py --file <path_to_shapefile> --version <version_id>

Example:
    python etl/import_geomolg.py \\
        --file etl/data/geomolg/nablus_master_plan.shp \\
        --version "GeoMOLG_2024-08-08" \\
        --effective-date "2024-01-01"

The script will:
1. Load shapefile and validate CRS (with hard assertion)
2. Reproject to EPSG:4326 if needed (per blueprint directive)
3. Map GeoMOLG fields to our schema
4. Validate geometries
5. Insert into zoning_plans with provenance metadata
6. Log operation to spatial_data_changelog
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
from tqdm import tqdm

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from common import (
    validate_and_reproject_gdf,
    validate_geometries,
    get_db_engine,
    get_db_session,
    log_spatial_data_change,
    get_nablus_filter,
    confirm_action,
)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Import GeoMOLG master plan zoning data"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to shapefile (e.g., nablus_master_plan.shp)",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Source version identifier (e.g., GeoMOLG_2024-08-08)",
    )
    parser.add_argument(
        "--effective-date",
        required=True,
        help="Effective date in YYYY-MM-DD format",
    )
    parser.add_argument(
        "--executed-by",
        default="system",
        help="Username of person executing import (default: system)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )
    parser.add_argument(
        "--governorate",
        default=None,
        help="Filter to specific governorate (default: from env ACTIVE_GOVERNORATE)",
    )
    return parser.parse_args()


def map_geomolg_fields(gdf: gpd.GeoDataFrame) -> dict:
    """Map GeoMOLG field names to our schema.
    
    GeoMOLG exports may have varying field names depending on
    the export format and language settings. This function attempts
    to intelligently map common field name variants.
    
    Args:
        gdf: Input GeoDataFrame from GeoMOLG
    
    Returns:
        Dictionary mapping our schema fields to GeoMOLG column names
    """
    columns = [col.upper() for col in gdf.columns]
    column_map = {}
    
    # Locality / City name
    locality_candidates = ['LOCALITY', 'CITY_NAME', 'CITY', 'TOWN', 'VILLAGE', 
                          'اسم_المدينة', 'المدينة', 'MUNICIPAL']
    for candidate in locality_candidates:
        if candidate in columns:
            column_map['locality'] = gdf.columns[columns.index(candidate)]
            break
    
    # Zoning code
    code_candidates = ['ZONE_CODE', 'LAND_USE_CODE', 'CODE', 'رمز_المنطقة', 
                      'ZONECODE', 'LANDUSE']
    for candidate in code_candidates:
        if candidate in columns:
            column_map['zoning_code'] = gdf.columns[columns.index(candidate)]
            break
    
    # Zoning description
    desc_candidates = ['ZONE_DESC', 'LAND_USE_NAME', 'DESCRIPTION', 'DESC',
                      'وصف_المنطقة', 'ZONEDESC', 'LANDUSENAME']
    for candidate in desc_candidates:
        if candidate in columns:
            column_map['zoning_description'] = gdf.columns[columns.index(candidate)]
            break
    
    # Building height
    height_candidates = ['MAX_HEIGHT', 'HEIGHT_LIMIT', 'HEIGHT', 'الارتفاع_الأقصى',
                        'MAXHEIGHT', 'BUILD_HEIGHT']
    for candidate in height_candidates:
        if candidate in columns:
            column_map['max_building_height'] = gdf.columns[columns.index(candidate)]
            break
    
    # Floor area ratio
    far_candidates = ['FAR', 'FLOOR_AREA_RATIO', 'نسبة_البناء', 'FLOORRATIO',
                     'BUILD_RATIO']
    for candidate in far_candidates:
        if candidate in columns:
            column_map['max_floor_area_ratio'] = gdf.columns[columns.index(candidate)]
            break
    
    # Plan approval date
    approval_candidates = ['APPROVAL_DATE', 'APPROVE_DATE', 'تاريخ_التصديق',
                          'APPROVED', 'PLAN_DATE']
    for candidate in approval_candidates:
        if candidate in columns:
            column_map['plan_approval_date'] = gdf.columns[columns.index(candidate)]
            break
    
    return column_map


def load_and_prepare_data(
    filepath: str,
    source_version: str,
    effective_date: date,
    governorate_filter: str
) -> gpd.GeoDataFrame:
    """Load GeoMOLG data and prepare for import.
    
    Args:
        filepath: Path to shapefile
        source_version: Version identifier
        effective_date: Effective date for zoning
        governorate_filter: Governorate name to filter
    
    Returns:
        Prepared GeoDataFrame
    """
    print(f"📂 Loading data from {filepath}")
    gdf = gpd.read_file(filepath, encoding='utf-8')
    
    print(f"📊 Loaded {len(gdf)} features")
    print(f"   Columns: {list(gdf.columns)}")
    print(f"   CRS: {gdf.crs}")
    
    # Validate and reproject CRS (hard assertion per blueprint)
    gdf = validate_and_reproject_gdf(gdf, "GeoMOLG", assert_crs=True)
    
    # Validate geometries
    gdf = validate_geometries(gdf, "GeoMOLG")
    
    # Map GeoMOLG fields to our schema
    print(f"\n🗺️  Mapping GeoMOLG fields to schema...")
    field_map = map_geomolg_fields(gdf)
    print(f"   Mapped fields: {field_map}")
    
    # Check for required fields
    if 'locality' not in field_map:
        print("⚠️  WARNING: Could not find locality/city field")
        print(f"   Available columns: {list(gdf.columns)}")
        print("   Please update field_map in script or rename columns")
    
    if 'zoning_code' not in field_map:
        print("❌ ERROR: Could not find zoning_code field (required)")
        print(f"   Available columns: {list(gdf.columns)}")
        sys.exit(1)
    
    # Prepare output DataFrame
    prepared_data = {
        'geometry': gdf.geometry,
        'governorate': governorate_filter,  # Phase 1: All Nablus
        'source_version': source_version,
        'effective_date': effective_date,
    }
    
    # Add mapped fields
    for our_field, geomolg_field in field_map.items():
        prepared_data[our_field] = gdf[geomolg_field]
    
    # Fill missing fields with defaults
    if 'locality' not in prepared_data:
        prepared_data['locality'] = 'Unknown'
    
    if 'zoning_description' not in prepared_data:
        prepared_data['zoning_description'] = None
    
    if 'max_building_height' not in prepared_data:
        prepared_data['max_building_height'] = None
    
    if 'max_floor_area_ratio' not in prepared_data:
        prepared_data['max_floor_area_ratio'] = None
    
    if 'plan_approval_date' not in prepared_data:
        prepared_data['plan_approval_date'] = None
    
    gdf_prepared = gpd.GeoDataFrame(prepared_data, crs=gdf.crs)
    
    # Clean up zoning codes (remove whitespace, standardize)
    gdf_prepared['zoning_code'] = gdf_prepared['zoning_code'].astype(str).str.strip()
    
    # Remove rows with missing/invalid zoning code
    before = len(gdf_prepared)
    gdf_prepared = gdf_prepared[
        (gdf_prepared['zoning_code'].notna()) & 
        (gdf_prepared['zoning_code'] != '') &
        (gdf_prepared['zoning_code'] != 'None')
    ].copy()
    if len(gdf_prepared) < before:
        print(f"⚠️  Removed {before - len(gdf_prepared)} features with invalid zoning code")
    
    print(f"\n📋 Prepared data summary:")
    print(f"   Total features: {len(gdf_prepared)}")
    print(f"   Localities: {gdf_prepared['locality'].nunique()}")
    print(f"   Zoning codes: {gdf_prepared['zoning_code'].nunique()}")
    print(f"   Top 5 zones: {gdf_prepared['zoning_code'].value_counts().head().to_dict()}")
    
    return gdf_prepared


def import_to_database(gdf: gpd.GeoDataFrame, args) -> int:
    """Import prepared data to database.
    
    Args:
        gdf: Prepared GeoDataFrame
        args: Command line arguments
    
    Returns:
        Number of records inserted
    """
    if len(gdf) == 0:
        print("❌ No data to import")
        return 0
    
    # Confirmation prompt
    if not args.force:
        if not confirm_action(
            f"Import {len(gdf)} features to zoning_plans?"
        ):
            print("❌ Import cancelled by user")
            return 0
    
    print(f"\n🚀 Importing to database...")
    
    # Get database connection
    engine = get_db_engine(sync=True)
    session = get_db_session()
    
    try:
        # Import using GeoPandas to_postgis
        gdf.to_postgis(
            name='zoning_plans',
            con=engine,
            if_exists='append',
            index=False,
        )
        
        records_inserted = len(gdf)
        print(f"✅ Inserted {records_inserted} records")
        
        # Log to changelog
        log_spatial_data_change(
            session=session,
            table_name='zoning_plans',
            operation='INSERT',
            source_name='GeoMOLG',
            source_version=args.version,
            records_affected=records_inserted,
            import_method='manual_arcgis_export',
            executed_by=args.executed_by,
            notes=f"Master plan zoning, effective date: {args.effective_date}",
        )
        
        return records_inserted
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()


def main():
    """Main ETL workflow."""
    args = parse_args()
    
    print("=" * 70)
    print("GeoMOLG Master Plans Import")
    print("=" * 70)
    print(f"Source file: {args.file}")
    print(f"Version: {args.version}")
    print(f"Effective date: {args.effective_date}")
    print(f"Executed by: {args.executed_by}")
    print("=" * 70)
    print()
    
    # Verify runbook exists
    runbook_path = Path(__file__).parent / "geomolg_etl_runbook.md"
    if not runbook_path.exists():
        print("⚠️  WARNING: geomolg_etl_runbook.md not found!")
        print("   This runbook documents manual export procedures.")
    else:
        print(f"📖 Runbook found: {runbook_path}")
    
    # Parse effective date
    try:
        effective_date = date.fromisoformat(args.effective_date)
    except ValueError:
        print(f"❌ Invalid date format: {args.effective_date}")
        print("   Expected: YYYY-MM-DD (e.g., 2024-01-01)")
        sys.exit(1)
    
    # Get governorate filter
    governorate_filter = args.governorate or get_nablus_filter()
    
    # Load and prepare data
    gdf = load_and_prepare_data(
        filepath=args.file,
        source_version=args.version,
        effective_date=effective_date,
        governorate_filter=governorate_filter,
    )
    
    # Import to database
    records_inserted = import_to_database(gdf, args)
    
    print()
    print("=" * 70)
    if records_inserted > 0:
        print(f"✅ Import complete: {records_inserted} records")
        print("\n📝 Remember to update METADATA.txt with import details")
    else:
        print("⚠️  No records imported")
    print("=" * 70)


if __name__ == "__main__":
    main()
