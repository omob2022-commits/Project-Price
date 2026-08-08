# ETL Scripts for Palestine Land Valuation Platform

This directory contains Extract-Transform-Load (ETL) scripts for importing spatial data into the PostgreSQL + PostGIS database.

## Overview

The ETL pipeline handles three primary data sources:

1. **OCHA HDX** - Oslo Accords geopolitical boundaries (Areas A, B, C)
2. **GeoMOLG** - Palestinian master plan zoning data (manual export)
3. **Comps** - Verified comparable sales transactions

## Architecture Principles

Per blueprint directives, all ETL scripts implement:

- **CRS Hard Assertions**: All spatial data must have a defined CRS, enforced via assertions
- **Automatic Reprojection**: Data is reprojected to EPSG:4326 (WGS84) before import
- **Provenance Tracking**: `source_version` and `effective_date` recorded for all imports
- **Changelog Auditing**: All operations logged to `spatial_data_changelog` table
- **Phase 1 Filtering**: Data scoped to Nablus Governorate only

## Setup

### Install Dependencies

```bash
# From project root
pip install -r etl/requirements.txt
```

### Environment Variables

ETL scripts use the same `.env` file as the backend:

```bash
# backend/.env
DATABASE_URL_SYNC=postgresql://landval:password@localhost:5432/landval_db
ACTIVE_GOVERNORATE=Nablus
```

## Data Sources & Import Scripts

### 1. OCHA HDX (Oslo Accords Boundaries)

**Source**: https://data.humdata.org/dataset/oslo-accords-areas-west-bank

**Download Steps**:
1. Visit HDX dataset page
2. Download shapefile bundle (`.zip`)
3. Extract to `etl/data/ocha_hdx/`

**Import Command**:
```bash
python etl/import_ocha_hdx.py \
    --file etl/data/ocha_hdx/oslo_accords_areas.shp \
    --version "HDX_2024-08-08" \
    --effective-date "1995-09-28" \
    --executed-by "your_username"
```

**Notes**:
- Effective date: Use Oslo II Agreement date (1995-09-28) or actual boundary revision date
- Data is filtered to Nablus governorate automatically
- CRS validation and reprojection happen automatically

### 2. GeoMOLG (Master Plan Zoning)

**Source**: https://geomolg.pna.ps/ (manual export required)

**Export Steps**: See [`geomolg_etl_runbook.md`](./geomolg_etl_runbook.md) for detailed instructions

**Import Command**:
```bash
python etl/import_geomolg.py \
    --file etl/data/geomolg/nablus_master_plan.shp \
    --version "GeoMOLG_2024-08-08" \
    --effective-date "2024-01-01" \
    --executed-by "your_username"
```

**Important**:
- **Always** follow the runbook for consistent exports
- Document export in `etl/data/geomolg/METADATA.txt`
- Verify field mappings (script auto-detects common variants)
- Legal review required before production use (see runbook)

### 3. Comparable Sales (Comps)

**Source**: Real estate agents, court records, verified transactions

**Format**: CSV with required columns

**Import Command**:
```bash
# Script to be created when comp data is available
python etl/import_comps.py \
    --file etl/data/comps/nablus_comps_2024.csv \
    --version "Comps_2024-08-08" \
    --executed-by "your_username"
```

**Required CSV Columns**:
- `latitude`, `longitude` (WGS84 decimal degrees)
- `sale_date` (YYYY-MM-DD)
- `price_ils` (Israeli Shekels)
- `area_sqm` (square meters)
- `locality` (city/town/village name)
- `oslo_classification` (A, B, or C)
- Optional: `zoning_code`, `distance_to_road_m`, `has_water_access`, etc.

## Common Utilities (`common.py`)

All ETL scripts import shared functionality:

- **`validate_and_reproject_gdf()`** - CRS validation with hard assertions
- **`validate_geometries()`** - Check and repair invalid geometries
- **`get_db_engine()`** - Database connection factory
- **`log_spatial_data_change()`** - Changelog audit logging
- **`get_nablus_filter()`** - Phase 1 governorate filter

## Data Quality Checks

Before importing, verify:

- [ ] Shapefile opens without errors in QGIS
- [ ] Feature count is reasonable
- [ ] Geometry type is correct (Polygon/Point)
- [ ] Coordinate system is defined
- [ ] Required fields are present
- [ ] No duplicate features
- [ ] Arabic text displays correctly (if applicable)

## Monitoring & Auditing

### View Import History

```sql
SELECT 
    table_name,
    operation,
    source_name,
    source_version,
    records_affected,
    executed_by,
    executed_at
FROM spatial_data_changelog
ORDER BY executed_at DESC
LIMIT 20;
```

### Verify Data Provenance

```sql
-- Check geopolitical boundaries
SELECT 
    classification,
    governorate,
    source_version,
    effective_date,
    COUNT(*) as feature_count
FROM geopolitical_boundaries
GROUP BY classification, governorate, source_version, effective_date;

-- Check zoning plans
SELECT 
    governorate,
    source_version,
    COUNT(*) as feature_count,
    COUNT(DISTINCT zoning_code) as unique_zones
FROM zoning_plans
GROUP BY governorate, source_version;
```

## Troubleshooting

### CRS Assertion Failure

**Error**: `AssertionError: CRS assertion failed`

**Cause**: Shapefile has no `.prj` file or CRS is undefined

**Solution**:
1. Check if `.prj` file exists alongside `.shp`
2. Open in QGIS and define CRS manually
3. Re-export with correct CRS
4. Alternatively, disable assertion (not recommended): `assert_crs=False`

### Database Connection Failed

**Error**: `psycopg2.OperationalError: could not connect`

**Solution**:
1. Verify PostgreSQL is running: `docker-compose ps`
2. Check `DATABASE_URL_SYNC` in `.env`
3. Test connection: `psql -h localhost -U landval -d landval_db`
4. Ensure PostGIS extension is enabled (see migration docs)

### Import Fails with "relation does not exist"

**Error**: `psycopg2.errors.UndefinedTable: relation "table_name" does not exist`

**Solution**:
Run migrations first:
```bash
cd backend && ./scripts/migrate.sh upgrade
```

### Geometry Validation Errors

**Error**: `Invalid geometries found`

**Solution**:
The script automatically attempts repair with `buffer(0)`. If repair fails:
1. Open shapefile in QGIS
2. Run **Vector > Geometry Tools > Fix Geometries**
3. Save fixed version and re-run import

### Field Mapping Issues (GeoMOLG)

**Error**: `Could not find zoning_code field`

**Solution**:
1. Open shapefile in QGIS and inspect attribute table
2. Update `map_geomolg_fields()` function in `import_geomolg.py`
3. Add your field names to the candidates list
4. Re-run import

## Best Practices

1. **Always backup** the database before bulk imports
2. **Test on staging** environment first
3. **Document exports** in METADATA.txt files
4. **Verify data quality** before import (see checklist above)
5. **Use version identifiers** with dates (e.g., `HDX_2024-08-08`)
6. **Track provenance**: Never skip `source_version` and `effective_date`
7. **Update changelog**: Script logs automatically, but add notes manually if needed

## Phase 1 Scope

Current scripts filter all imports to **Nablus Governorate** only. This is controlled by:

- Environment variable: `ACTIVE_GOVERNORATE=Nablus`
- Script parameter: `--governorate Nablus`

For Phase 2+ expansion to other governorates:

1. Update `ACTIVE_GOVERNORATE` or pass `--governorate` parameter
2. Re-run imports for each new region
3. No code changes required (schema is already dynamic)

## Data Freshness

Spatial data has different update frequencies:

| Data Type | Update Frequency | Check How |
|-----------|------------------|-----------|
| Geopolitical Boundaries | Rarely (years) | Monitor Oslo Accord changes |
| Zoning Plans | Occasionally (quarterly) | Check GeoMOLG portal |
| Comps | Frequently (monthly) | Real estate agent updates |

Set up periodic checks and re-imports as data is updated.

## Contact & Support

- **ETL Issues**: [Your team contact]
- **OCHA HDX Support**: Via HDX platform
- **GeoMOLG Support**: [Ministry of Local Government contact]

## See Also

- [`geomolg_etl_runbook.md`](./geomolg_etl_runbook.md) - Detailed GeoMOLG export instructions
- [`../backend/alembic/README.md`](../backend/alembic/README.md) - Database migration docs
- [OCHA HDX Platform](https://data.humdata.org/)
- [GeoMOLG Portal](https://geomolg.pna.ps/)
