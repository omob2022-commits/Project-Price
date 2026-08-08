"""
API v1 router aggregation.

All versioned endpoints are collected here and exposed via api_router.
"""

from fastapi import APIRouter

from app.api.v1 import auth, valuation, parcels, users

api_router = APIRouter()

# Include sub-routers
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(valuation.router, prefix="/valuation", tags=["valuation"])
api_router.include_router(parcels.router, prefix="/parcels", tags=["parcels"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
