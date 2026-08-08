"""
Pydantic schemas for parcel data and saved parcels.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ParcelResponse(BaseModel):
    """Schema for parcel data in responses."""
    id: int
    governorate: str
    area_sqm: float
    oslo_classification: Optional[str] = None
    zoning_code: Optional[str] = None
    zoning_description: Optional[str] = None
    valuation_min_per_sqm: Optional[float] = None
    valuation_max_per_sqm: Optional[float] = None
    valuation_confidence: Optional[float] = None
    valuation_date: Optional[datetime] = None
    comp_count: Optional[int] = None
    degrees_of_freedom: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class SavedParcelCreate(BaseModel):
    """Schema for saving a parcel."""
    parcel_id: int
    notes: Optional[str] = Field(None, max_length=5000)


class SavedParcelResponse(BaseModel):
    """Schema for saved parcel data in responses."""
    id: int
    user_id: int
    parcel_id: int
    notes: Optional[str] = None
    saved_at: datetime
    parcel: Optional[ParcelResponse] = None
    
    class Config:
        from_attributes = True
