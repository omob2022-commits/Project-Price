"""
Pydantic schemas for valuation requests and responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ValuationRequest(BaseModel):
    """Schema for valuation request (extends valuation engine model)."""
    latitude: float = Field(..., ge=-90, le=90, description="WGS84 latitude")
    longitude: float = Field(..., ge=-180, le=180, description="WGS84 longitude")
    area_sqm: float = Field(..., gt=0, description="Parcel area in square meters")
    oslo_classification: str = Field(..., pattern="^(A|B|C)$", description="Oslo classification")
    
    # Optional features
    zoning_code: Optional[str] = None
    distance_to_road_m: Optional[float] = Field(None, ge=0)
    distance_to_city_center_m: Optional[float] = Field(None, ge=0)
    has_water_access: Optional[bool] = None
    has_electricity_access: Optional[bool] = None
    slope_category: Optional[str] = Field(None, pattern="^(flat|moderate|steep)$")


class ValuationResponse(BaseModel):
    """Schema for valuation result response."""
    valuation_min_per_sqm: float
    valuation_max_per_sqm: float
    valuation_midpoint_per_sqm: float
    valuation_confidence: float
    comp_count: int
    degrees_of_freedom: int
    model_type: str
    shrinkage_weight: float
    valuation_date: datetime
    warnings: list[str]
    
    # Disclaimer per blueprint directive
    disclaimer: str = (
        "This valuation is an estimate, not an appraisal. "
        "Actual market values may differ. Consult a licensed appraiser "
        "for official valuations."
    )
