"""
Data models for valuation engine.

Defines input/output structures for valuation requests and results.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ValuationRequest(BaseModel):
    """Request for land parcel valuation.
    
    Attributes:
        latitude: WGS84 latitude of parcel centroid
        longitude: WGS84 longitude of parcel centroid
        area_sqm: Parcel area in square meters
        oslo_classification: Area classification (A, B, or C)
        zoning_code: Zoning designation (optional)
        distance_to_road_m: Distance to nearest paved road (optional)
        distance_to_city_center_m: Distance to governorate capital (optional)
        has_water_access: Water infrastructure availability (optional)
        has_electricity_access: Electricity infrastructure availability (optional)
        slope_category: Terrain classification (optional: flat, moderate, steep)
    """
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


class ValuationResult(BaseModel):
    """Result of land parcel valuation.
    
    Attributes:
        valuation_min_per_sqm: Lower bound of valuation range (₪/m²)
        valuation_max_per_sqm: Upper bound of valuation range (₪/m²)
        valuation_confidence: Statistical confidence level (e.g., 0.90)
        comp_count: Number of comparable sales used
        degrees_of_freedom: N - p - 1 for regression model
        model_type: Type of model used (regression, shrinkage, or heuristic)
        shrinkage_weight: Weight applied to regression (0-1, 1 = full regression)
        valuation_date: When the valuation was computed
        warnings: Any warnings about data quality or model limitations
    """
    valuation_min_per_sqm: float = Field(..., description="Lower bound (₪/m²)")
    valuation_max_per_sqm: float = Field(..., description="Upper bound (₪/m²)")
    valuation_confidence: float = Field(..., ge=0, le=1, description="Confidence level")
    
    comp_count: int = Field(..., ge=0, description="Number of comps used")
    degrees_of_freedom: int = Field(..., description="Residual degrees of freedom")
    
    model_type: str = Field(..., description="regression, shrinkage, or heuristic")
    shrinkage_weight: float = Field(..., ge=0, le=1, description="Regression weight")
    
    valuation_date: datetime = Field(..., description="Computation timestamp")
    warnings: list[str] = Field(default_factory=list, description="Data quality warnings")
    
    @property
    def valuation_midpoint_per_sqm(self) -> float:
        """Midpoint of valuation range."""
        return (self.valuation_min_per_sqm + self.valuation_max_per_sqm) / 2
    
    @property
    def valuation_range_width(self) -> float:
        """Width of valuation range."""
        return self.valuation_max_per_sqm - self.valuation_min_per_sqm


class CompData(BaseModel):
    """Comparable sale data for model training.
    
    Internal model used by valuation engine.
    """
    price_per_sqm: float
    area_sqm: float
    oslo_classification: str
    distance_to_road_m: Optional[float] = None
    distance_to_city_center_m: Optional[float] = None
    has_water_access: Optional[bool] = None
    has_electricity_access: Optional[bool] = None
    slope_category: Optional[str] = None
    zoning_code: Optional[str] = None
    sale_date: datetime
