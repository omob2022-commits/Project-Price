"""
FastAPI application entry point for Palestine Land Valuation Platform.

Per blueprint directive: "All endpoints must be versioned from day one 
(e.g., `/api/v1/valuation`)."
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting Palestine Land Valuation Platform API")
    print(f"📍 Phase 1 Scope: {settings.active_governorate} Governorate")
    yield
    # Shutdown
    print("👋 Shutting down API")


app = FastAPI(
    title="Palestine Land Valuation Platform",
    description=(
        "A PropTech web application for calculating land parcel values in Palestine. "
        "Combats information asymmetry through data-driven valuation ranges based on "
        "geospatial location, geopolitical classifications, and market comparables."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router (versioned endpoints)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Palestine Land Valuation Platform API",
        "version": "0.1.0",
        "phase": "Phase 1 - Nablus Governorate",
        "docs": "/docs",
        "api_base": "/api/v1",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "landval-api",
        "version": "0.1.0",
    }
