# GeoMOLG ETL Runbook

**Required per blueprint directive**: "Because GeoMOLG requires manual ArcGIS exports, developers must create a `geomolg_etl_runbook.md` detailing the exact export steps, filters, and layer order."

## Overview

GeoMOLG (المخططات الهيكلية المصدقة / Approved Structural Plans) is the Palestinian Ministry of Local Government's master plan database. It contains official zoning designations that define permitted land uses, building heights, and development density.

**Important**: GeoMOLG data requires manual export from their ArcGIS portal. This runbook documents the exact steps to ensure consistent, reproducible exports.

## Prerequisites

- Access to GeoMOLG portal (https://geomolg.pna.ps/)
- ArcGIS-compatible viewer or QGIS
- Network connection (GeoMOLG may have authentication requirements)

## Phase 1: Nablus Governorate Only

For Phase 1, we only need master plan data for **Nablus Governorate**.

## Export Procedure

### Step 1: Access GeoMOLG Portal

1. Navigate to https://geomolg.pna.ps/
2. Log in (if authentication is required)
3. Navigate to the map viewer

### Step 2: Filter to Nablus Governorate

1. In the layer panel, locate the **Governorate** or **محافظة** layer
2. Apply filter: `Governorate = 'Nablus'` or `محافظة = 'نابلس'`
3. Verify that the map view is now limited to Nablus region

### Step 3: Select Master Plan Layers

Enable the following layers (in order of importance):

1. **Approved Master Plans** (المخططات الهيكلية المصدقة)
   - This is the primary zoning layer
   - Contains zoning codes and designations

2. **Land Use Zones** (مناطق استعمالات الأراضي)
   - Detailed zoning classifications
   - Should align with master plans

3. **Building Restrictions** (قيود البناء) [Optional]
   - Height limits
   - Setback requirements
   - Floor area ratios

### Step 4: Export Layers

For **each layer** selected above:

1. Right-click on layer name
2. Select **Export Data** or **تصدير البيانات**
3. Configure export settings:
   - **Format**: Shapefile (.shp)
   - **Coordinate System**: Keep original (will be reprojected by ETL script)
   - **Extent**: Current map extent (Nablus only)
   - **Features**: Selected features or all features in view
4. Click **Export** and save to local directory

### Step 5: Organize Exported Files

Create the following directory structure:

```
etl/data/geomolg/
├── nablus_master_plan.shp
├── nablus_master_plan.shx
├── nablus_master_plan.dbf
├── nablus_master_plan.prj
├── nablus_master_plan.cpg  (if available)
└── METADATA.txt  (create this manually)
```

### Step 6: Document Export Metadata

Create `METADATA.txt` in the same directory with the following information:

```
Export Date: YYYY-MM-DD
Export Time: HH:MM UTC
GeoMOLG Portal Version: [check portal footer]
Governorate: Nablus
Layers Exported:
  - Layer Name: Approved Master Plans
    Feature Count: XXX
    Date Range: [earliest plan date] to [latest plan date]
Coordinate System: [from .prj file]
Exported By: [your name]
Notes: [any special conditions or observations]
```

## Field Mapping Reference

The ETL script expects the following fields. Map your shapefile columns accordingly:

| Our Schema Field | Common GeoMOLG Field Names |
|------------------|----------------------------|
| `locality` | `LOCALITY`, `CITY_NAME`, `اسم_المدينة` |
| `zoning_code` | `ZONE_CODE`, `LAND_USE_CODE`, `رمز_المنطقة` |
| `zoning_description` | `ZONE_DESC`, `LAND_USE_NAME`, `وصف_المنطقة` |
| `max_building_height` | `MAX_HEIGHT`, `HEIGHT_LIMIT`, `الارتفاع_الأقصى` |
| `max_floor_area_ratio` | `FAR`, `FLOOR_AREA_RATIO`, `نسبة_البناء` |
| `plan_approval_date` | `APPROVAL_DATE`, `تاريخ_التصديق` |

**Note**: If your export has different field names, you'll need to update the ETL script's column mapping section.

## Common Issues & Troubleshooting

### Issue: Export Button Grayed Out

**Cause**: Insufficient permissions or layer not selectable

**Solution**:
- Verify you're logged in with appropriate credentials
- Try selecting features first, then export selected only
- Contact GeoMOLG support for data access

### Issue: Exported Shapefile is Empty

**Cause**: Filter too restrictive or no features in view

**Solution**:
- Zoom out to ensure Nablus is fully in view
- Clear any additional filters beyond governorate
- Check if layer has data for Nablus (some layers may be incomplete)

### Issue: Coordinate System Unknown

**Cause**: Missing or corrupted .prj file

**Solution**:
- Common Palestinian CRS options:
  - **EPSG:28192** (Palestine 1923 / Palestine Grid)
  - **EPSG:2039** (Israel TM Grid)
  - **EPSG:32636** (WGS 84 / UTM zone 36N)
- Check with GeoMOLG documentation or support
- The ETL script will reproject regardless, but correct input CRS is important

### Issue: Arabic Text Garbled

**Cause**: Character encoding mismatch

**Solution**:
- Ensure .cpg file is present (should contain `UTF-8` or `windows-1256`)
- If missing, create `.cpg` file with content: `UTF-8`
- Open in QGIS to verify encoding before running ETL

## Data Quality Checks

Before running the ETL script, verify:

- [ ] Shapefile opens in QGIS/ArcGIS without errors
- [ ] Feature count is reasonable (Nablus should have 50-200+ zones)
- [ ] Geometry type is Polygon or MultiPolygon
- [ ] Required fields are present (see Field Mapping Reference)
- [ ] Arabic text displays correctly
- [ ] Coordinate system is defined (.prj file exists)
- [ ] METADATA.txt is complete and accurate

## Running the ETL Script

Once export is complete and verified:

```bash
python etl/import_geomolg.py \
    --file etl/data/geomolg/nablus_master_plan.shp \
    --version "GeoMOLG_2024-08-08" \
    --effective-date "2024-01-01" \
    --executed-by "your_username"
```

## Legal & Licensing

**CRITICAL**: Per blueprint directive: "Conduct a legal review of GeoMOLG's Terms of Service for commercial/public use before scaling past the academic pilot phase."

### Current Status (Phase 1)
- Usage: Academic pilot / proof of concept
- Scope: Nablus only
- Distribution: Internal only

### Before Production
- [ ] Review GeoMOLG Terms of Service
- [ ] Obtain written permission for commercial use
- [ ] Clarify data redistribution rights
- [ ] Document licensing terms in project documentation
- [ ] Add appropriate attribution to UI

## Data Update Frequency

Master plans change infrequently (every few years), but should be monitored:

- **Recommended frequency**: Quarterly check
- **Update trigger**: New master plan approval announcements
- **Version tracking**: Use approval date as version identifier

## Contact Information

- **GeoMOLG Support**: [Contact information if available]
- **Ministry of Local Government**: [Contact information]
- **Data Steward** (Internal): [Your team's contact]

## Changelog

| Date | Changes | Updated By |
|------|---------|------------|
| 2026-08-08 | Initial runbook creation | System |
| | | |

## Appendix: Alternative Data Sources

If GeoMOLG access is unavailable:

1. **OpenStreetMap**: Has some zoning data, but incomplete
2. **Direct Municipal Contact**: Some municipalities publish plans on their websites
3. **Palestinian Central Bureau of Statistics**: May have aggregated data

Note: These alternatives may lack official approval status and should be marked with lower confidence.
