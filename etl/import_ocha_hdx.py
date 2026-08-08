#!/usr/bin/env python3
"""
OCHA HDX Oslo Accords Areas ETL Script

Imports Oslo Accords geopolitical boundaries (Areas A, B, C) from 
OCHA Humanitarian Data Exchange (HDX) into the geopolitical_boundaries table.

Data Source: https://data.humdata.org/dataset/oslo-accords-areas-west-bank

Usage:
    python etl/import_ocha_hdx.py --file <path_to_shapefile> --version <version_id>

Example:
    python etl/import_ocha_hdx.py \\
        --file etl/data/ocha_hdx/oslo_accords_areas.shp \\
        --version "HDX_2024-08-08" \\
        --effective-date "1995-09-28"

The script will:
1. Load shapefile and validate CRS
2. Reproject to EPSG:4326 if needed (per blueprint directive)
3. Filter to Nablus governorate only (Phase 1)
4. Validate geometries
5. Insert into geopolitical_boundaries with provenance metadata
6. Log operation to spatial_data_changelog
"""

import argparse
import sys
from datetime import date
from pathlib import Path

import geopandas as gpd
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
        description="Import OCHA HDX Oslo Accords boundaries"
    )
    parser.add_argument(
        "--file",
        required=True,
        help="Path to shapefile (e.g., oslo_accords_areas.shp)",
    )
    parser.add_argument(
        "--version",
        required=True,
        help="Source version identifier (e.g., HDX_2024-08-08)",
    )
    parser.add_argument(
        "--effective-date",
        required=True,
        help="Effective date in YYYY-MM-DD format (e.g., 1995-09-28 for Oslo II)",
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


def load_and_prepare_data(
    filepath: str,
    source_version: str,
    effective_date: date,
    governorate_filter: str
) -> gpd.GeoDataFrame:
    """Load HDX data and prepare for import.
    
    Args:
        filepath: Path to shapefile
        source_version: Version identifier
        effective_date: Effective date for boundaries
        governorate_filter: Governorate name to filter
    
    Returns:
        Prepared GeoDataFrame
    """
    print(f"📂 Loading data from {filepath}")
    gdf = gpd.read_file(filepath)
    
    print(f"📊 Loaded {len(gdf)} features")
    print(f"   Columns: {list(gdf.columns)}")
    print(f"   CRS: {gdf.crs}")
    
    # Validate and reproject CRS (hard assertion per blueprint)
    gdf = validate_and_reproject_gdf(gdf, "OCHA HDX", assert_crs=True)
    
    # Validate geometries
    gdf = validate_geometries(gdf, "OCHA HDX")
    
    # Filter to target governorate (Phase 1: Nablus only)
    if governorate_filter:
        print(f"🔍 Filtering to governorate: {governorate_filter}")
        
        # HDX data might use different column names - try common variants
        gov_columns = [col for col in gdf.columns if 'gov' in col.lower() or 'district' in col.lower()]
        
        if gov_columns:
            gov_col = gov_columns[0]
            print(f"   Using column: {gov_col}")
            initial_count = len(gdf)
            gdf = gdf[gdf[gov_col].str.contains(governorate_filter, case=False, na=False)].copy()
            print(f"   Filtered: {initial_count} → {len(gdf)} features")
        else:
            print(f"⚠️  WARNING: No governorate column found, importing all data")
    
    # Prepare output columns
    # Map HDX columns to our schema
    # (Adjust these mappings based on actual HDX shapefile structure)
    gdf_prepared = gpd.GeoDataFrame({
        'geometry': gdf.geometry,
        'classification': gdf.get('AREA', gdf.get('classification', gdf.get('area_class', 'Unknown'))),
        'governorate': gdf.get('GOV_NAME', gdf.get('governorate', governorate_filter)),
        'source_version': source_version,
        'effective_date': effective_date,
    }, crs=gdf.crs)
    
    # Clean up classification values (ensure A, B, or C)
    gdf_prepared['classification'] = gdf_prepared['classification'].str.strip().str.upper()
    gdf_prepared['classification'] = gdf_prepared['classification'].str.extract(r'(A|B|C)', expand=False)
    
    # Remove any rows with missing classification
    before = len(gdf_prepared)
    gdf_prepared = gdf_prepared.dropna(subset=['classification']).copy()
    if len(gdf_prepared) < before:
        print(f"⚠️  Removed {before - len(gdf_prepared)} features with invalid classification")
    
    print(f"\n📋 Prepared data summary:")
    print(f"   Total features: {len(gdf_prepared)}")
    print(f"   Classifications: {gdf_prepared['classification'].value_counts().to_dict()}")
    print(f"   Governorates: {gdf_prepared['governorate'].unique().tolist()}")
    
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
            f"Import {len(gdf)} features to geopolitical_boundaries?"
        ):
            print("❌ Import cancelled by user")
            return 0
    
    print(f"\n🚀 Importing to database...")
    
    # Get database connection
    engine = get_db_engine(sync=True)
    session = get_db_session()
    
    try:
        # Import using GeoPandas to_postgis
        # This handles geometry conversion automatically
        gdf.to_postgis(
            name='geopolitical_boundaries',
            con=engine,
            if_exists='append',
            index=False,
        )
        
        records_inserted = len(gdf)
        print(f"✅ Inserted {records_inserted} records")
        
        # Log to changelog
        log_spatial_data_change(
            session=session,
            table_name='geopolitical_boundaries',
            operation='INSERT',
            source_name='OCHA HDX',
            source_version=args.version,
            records_affected=records_inserted,
            import_method='geopandas_shapefile',
            executed_by=args.executed_by,
            notes=f"Oslo Accords boundaries, effective date: {args.effective_date}",
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
    print("OCHA HDX Oslo Accords Areas Import")
    print("=" * 70)
    print(f"Source file: {args.file}")
    print(f"Version: {args.version}")
    print(f"Effective date: {args.effective_date}")
    print(f"Executed by: {args.executed_by}")
    print("=" * 70)
    print()
    
    # Parse effective date
    try:
        effective_date = date.fromisoformat(args.effective_date)
    except ValueError:
        print(f"❌ Invalid date format: {args.effective_date}")
        print("   Expected: YYYY-MM-DD (e.g., 1995-09-28)")
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
    else:
        print("⚠️  No records imported")
    print("=" * 70)


if __name__ == "__main__":
    main()
