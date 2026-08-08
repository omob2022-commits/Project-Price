"""
Parcel endpoints for querying and retrieving land parcels.

Provides spatial queries using PostGIS ST_* functions.
"""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from geoalchemy2 import Geography
from geoalchemy2.functions import ST_AsGeoJSON, ST_Distance, ST_GeomFromText, ST_DWithin
from sqlalchemy import select, cast, String
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DatabaseSession
from app.models.parcel import Parcel
from app.schemas.parcel import ParcelResponse

router = APIRouter()


@router.get("/{parcel_id}", response_model=ParcelResponse)
async def get_parcel(parcel_id: int, db: DatabaseSession):
    """Get parcel by ID.
    
    Args:
        parcel_id: Parcel ID
        db: Database session
    
    Returns:
        Parcel data
    
    Raises:
        HTTPException: If parcel not found
    """
    result = await db.execute(select(Parcel).where(Parcel.id == parcel_id))
    parcel = result.scalar_one_or_none()
    
    if not parcel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parcel not found",
        )
    
    return ParcelResponse.model_validate(parcel)


@router.get("/", response_model=list[ParcelResponse])
async def search_parcels(
    db: DatabaseSession,
    governorate: Optional[str] = Query(None, description="Filter by governorate"),
    oslo_classification: Optional[str] = Query(None, pattern="^(A|B|C)$", description="Filter by Oslo area"),
    min_area_sqm: Optional[float] = Query(None, ge=0, description="Minimum area in m²"),
    max_area_sqm: Optional[float] = Query(None, ge=0, description="Maximum area in m²"),
    limit: int = Query(50, ge=1, le=100, description="Results limit"),
    offset: int = Query(0, ge=0, description="Results offset"),
):
    """Search parcels with filters.
    
    Args:
        db: Database session
        governorate: Filter by governorate name
        oslo_classification: Filter by Oslo classification
        min_area_sqm: Minimum parcel area
        max_area_sqm: Maximum parcel area
        limit: Maximum results to return
        offset: Pagination offset
    
    Returns:
        List of parcels matching filters
    """
    query = select(Parcel)
    
    # Apply filters
    if governorate:
        query = query.where(Parcel.governorate == governorate)
    
    if oslo_classification:
        query = query.where(Parcel.oslo_classification == oslo_classification)
    
    if min_area_sqm is not None:
        query = query.where(Parcel.area_sqm >= min_area_sqm)
    
    if max_area_sqm is not None:
        query = query.where(Parcel.area_sqm <= max_area_sqm)
    
    # Apply pagination
    query = query.offset(offset).limit(limit)
    
    result = await db.execute(query)
    parcels = result.scalars().all()
    
    return [ParcelResponse.model_validate(p) for p in parcels]


@router.get("/nearby/", response_model=list[ParcelResponse])
async def search_nearby_parcels(
    db: DatabaseSession,
    latitude: float = Query(..., ge=-90, le=90, description="Center latitude (WGS84)"),
    longitude: float = Query(..., ge=-180, le=180, description="Center longitude (WGS84)"),
    radius_m: float = Query(1000, ge=0, le=10000, description="Search radius in meters"),
    limit: int = Query(20, ge=1, le=50, description="Results limit"),
):
    """Search parcels near a geographic point using PostGIS geodesic distance.
    
    Uses ST_DWithin with geography cast for true geodesic distance in meters,
    not Euclidean degree-based approximation.
    
    Args:
        db: Database session
        latitude: Center point latitude (WGS84)
        longitude: Center point longitude (WGS84)
        radius_m: Search radius in meters (true geodesic distance)
        limit: Maximum results to return
    
    Returns:
        List of parcels within radius, ordered by geodesic distance
    """
    # Create point geometry (SRID 4326 = WGS84)
    point = f"SRID=4326;POINT({longitude} {latitude})"
    
    # Query using ST_DWithin with geography cast for true geodesic distance
    # This computes actual great-circle distance in meters, not degree approximation
    query = (
        select(Parcel)
        .where(
            ST_DWithin(
                cast(Parcel.geometry, Geography),
                cast(ST_GeomFromText(point), Geography),
                radius_m,  # meters, no conversion needed
            )
        )
        .order_by(
            ST_Distance(
                cast(Parcel.geometry, Geography),
                cast(ST_GeomFromText(point), Geography),
            )
        )
        .limit(limit)
    )
    
    result = await db.execute(query)
    parcels = result.scalars().all()
    
    return [ParcelResponse.model_validate(p) for p in parcels]
