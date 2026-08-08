"""
Valuation endpoint for computing land parcel valuations.

Integrates the valuation engine with the API, fetching comparable sales
from the database and returning valuation ranges.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, ST_GeomFromText
from sqlalchemy import select, cast

from app.api.deps import DatabaseSession
from app.core.config import settings
from app.models.comp import Comp
from app.schemas.valuation import ValuationRequest as ValuationRequestSchema
from app.schemas.valuation import ValuationResponse
from app.valuation import ValuationEngine
from app.valuation.models import ValuationRequest, CompData

router = APIRouter()


@router.post("/compute", response_model=ValuationResponse)
async def compute_valuation(request: ValuationRequestSchema, db: DatabaseSession):
    """Compute land parcel valuation.
    
    Per blueprint: "The engine outputs a valuation range (e.g., ₪X–Y/m²), 
    not a point estimate, based on comparable data points (comps) table."
    
    Also per blueprint: "The UI must feature a visible disclaimer that 
    valuations are estimates, not appraisals."
    
    Workflow:
    1. Receive parcel characteristics
    2. Query comparable sales within radius using PostGIS
    3. Filter comps by governorate and recency
    4. Pass comps to valuation engine
    5. Return valuation range with confidence interval
    
    Args:
        request: Valuation request with parcel characteristics
        db: Database session
    
    Returns:
        Valuation result with range and metadata
    """
    # Create point geometry for spatial query
    point = f"SRID=4326;POINT({request.longitude} {request.latitude})"
    
    # Define comp search parameters
    comp_radius_m = settings.default_comp_radius_m  # True geodesic meters
    max_comp_age_days = 730  # 2 years
    min_comp_date = datetime.now(timezone.utc) - timedelta(days=max_comp_age_days)
    
    # Query comparable sales using PostGIS geodesic distance
    # Cast to geography for true great-circle distance in meters, not degree approximation
    query = (
        select(Comp)
        .where(
            # Spatial filter: within radius using true geodesic distance
            ST_Distance(
                cast(Comp.geometry, Geography),
                cast(ST_GeomFromText(point), Geography),
            ) <= comp_radius_m,
            # Temporal filter: recent sales only
            Comp.sale_date >= min_comp_date,
            # Oslo classification filter: same or similar area
            Comp.oslo_classification == request.oslo_classification,
        )
        .order_by(
            # Order by geodesic distance (nearest first)
            ST_Distance(
                cast(Comp.geometry, Geography),
                cast(ST_GeomFromText(point), Geography),
            )
        )
        .limit(100)  # Limit to top 100 nearest comps
    )
    
    result = await db.execute(query)
    comp_records = result.scalars().all()
    
    # Convert database records to valuation engine format
    comps = [
        CompData(
            price_per_sqm=float(comp.price_per_sqm),
            area_sqm=float(comp.area_sqm),
            oslo_classification=comp.oslo_classification,
            distance_to_road_m=float(comp.distance_to_road_m) if comp.distance_to_road_m else None,
            distance_to_city_center_m=float(comp.distance_to_city_center_m) if comp.distance_to_city_center_m else None,
            has_water_access=comp.has_water_access,
            has_electricity_access=comp.has_electricity_access,
            slope_category=comp.slope_category,
            zoning_code=comp.zoning_code,
            sale_date=comp.sale_date.replace(tzinfo=timezone.utc) if comp.sale_date.tzinfo is None else comp.sale_date,
        )
        for comp in comp_records
    ]
    
    # Convert request schema to valuation engine format
    valuation_request = ValuationRequest(
        latitude=request.latitude,
        longitude=request.longitude,
        area_sqm=request.area_sqm,
        oslo_classification=request.oslo_classification,
        zoning_code=request.zoning_code,
        distance_to_road_m=request.distance_to_road_m,
        distance_to_city_center_m=request.distance_to_city_center_m,
        has_water_access=request.has_water_access,
        has_electricity_access=request.has_electricity_access,
        slope_category=request.slope_category,
    )
    
    # Initialize valuation engine and compute valuation
    engine = ValuationEngine()
    valuation_result = engine.compute_valuation(valuation_request, comps)
    
    # Convert to API response schema
    return ValuationResponse(
        valuation_min_per_sqm=valuation_result.valuation_min_per_sqm,
        valuation_max_per_sqm=valuation_result.valuation_max_per_sqm,
        valuation_midpoint_per_sqm=valuation_result.valuation_midpoint_per_sqm,
        valuation_confidence=valuation_result.valuation_confidence,
        comp_count=valuation_result.comp_count,
        degrees_of_freedom=valuation_result.degrees_of_freedom,
        model_type=valuation_result.model_type,
        shrinkage_weight=valuation_result.shrinkage_weight,
        valuation_date=valuation_result.valuation_date,
        warnings=valuation_result.warnings,
    )
