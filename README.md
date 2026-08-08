# Palestine Land Valuation Platform

A scalable PropTech web application designed to calculate and display the relative value of land parcels in Palestine. The platform combats information asymmetry and pricing bias by providing data-driven valuation ranges based on geospatial location, geopolitical classifications, real comps, and surrounding infrastructure.

**Phase 1 Scope:** Nablus Governorate (pilot implementation)

## 🎯 Project Overview

### The Problem

Land transactions in Palestine suffer from:
- **Information asymmetry** - Buyers lack access to comparable sales data
- **Pricing bias** - Geopolitical classifications (Oslo Areas A, B, C) dramatically affect values
- **Opacity** - No centralized source for data-driven land valuations

### The Solution

This platform provides:
- **Transparent valuations** - Statistical confidence intervals, not point estimates
- **Geospatial context** - Integration with Oslo Accords boundaries and master plans
- **Data provenance** - Full audit trail of data sources and versions
- **Privacy-first** - User searches remain strictly private

## 🏗️ Architecture

### Technology Stack

**Backend:**
- **FastAPI** (Python 3.11+) - Async web framework with automatic OpenAPI docs
- **PostgreSQL 16 + PostGIS 3.4** - Spatial database with geometry types and GiST indexes
- **SQLAlchemy 2.0** - Async ORM with type hints
- **Alembic** - Database migrations
- **GeoPandas** - Geospatial ETL processing

**Valuation Engine:**
- **scikit-learn** - Ridge regression with shrinkage estimator
- **scipy** - T-distribution confidence intervals
- **NumPy/Pandas** - Feature engineering and data manipulation

**Authentication:**
- **JWT** (python-jose) - Stateless token-based auth
- **bcrypt** - Secure password hashing

**Infrastructure:**
- **Docker + Docker Compose** - Containerized deployment
- **uvicorn** - ASGI server

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (TBD)                        │
│                   MapLibre GL + React/Vue                    │
└───────────────────────┬─────────────────────────────────────┘
                        │ REST API (JSON)
┌───────────────────────▼─────────────────────────────────────┐
│                    FastAPI Backend                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Auth     │  │   Parcels    │  │  Valuation   │      │
│  │  /api/v1/*   │  │  /api/v1/*   │  │  /api/v1/*   │      │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘      │
│         │                  │                  │              │
│         └─────────┬────────┴──────────────────┘              │
│                   │                                          │
│         ┌─────────▼──────────┐                               │
│         │ Valuation Engine   │                               │
│         │ - Hedonic Reg.     │                               │
│         │ - Shrinkage Est.   │                               │
│         │ - T-distribution   │                               │
│         └─────────┬──────────┘                               │
└───────────────────┼──────────────────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────────────────┐
│              PostgreSQL + PostGIS Database                    │
│                                                               │
│  ┌───────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Users   │  │   Parcels    │  │    Comps     │          │
│  └───────────┘  └──────────────┘  └──────────────┘          │
│                                                               │
│  ┌───────────────────┐  ┌──────────────────────┐            │
│  │ Geopolitical      │  │    Zoning Plans      │            │
│  │ Boundaries (A/B/C)│  │    (GeoMOLG)         │            │
│  └───────────────────┘  └──────────────────────┘            │
│                                                               │
│  GiST Spatial Indexes: ST_Intersects, ST_DWithin, ST_Distance│
└───────────────────────────────────────────────────────────────┘
                    ▲
                    │ ETL Import
┌───────────────────┴──────────────────────────────────────────┐
│                    ETL Pipeline                               │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  OCHA HDX    │  │  GeoMOLG     │  │    Comps     │       │
│  │ Oslo Areas   │  │ Master Plans │  │ Market Data  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                                                               │
│  CRS Validation • Reprojection • Provenance • Changelog      │
└───────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (recommended)
- **Python 3.11+** (for local development)
- **PostgreSQL 16 + PostGIS 3.4** (if running without Docker)

### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone <repository-url>
cd Project-Price

# Copy environment file
cp .env.example backend/.env

# Edit backend/.env with your settings
nano backend/.env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec backend python -m alembic upgrade head

# Check status
docker-compose ps

# View logs
docker-compose logs -f backend
```

API will be available at http://localhost:8000

### Option 2: Local Development

```bash
# Install PostgreSQL + PostGIS
# macOS: brew install postgresql postgis
# Ubuntu: sudo apt-get install postgresql-16 postgis

# Create database
createdb landval_db
psql landval_db -c "CREATE EXTENSION postgis;"

# Set up Python environment
cd backend
python3.11 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
nano .env  # Edit database credentials

# Run migrations
./scripts/migrate.sh upgrade

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📊 Data Import (ETL)

### 1. OCHA HDX - Oslo Accords Boundaries

```bash
# Download from HDX
wget https://data.humdata.org/dataset/oslo-accords-areas-west-bank

# Extract to etl/data/ocha_hdx/

# Import
python etl/import_ocha_hdx.py \
    --file etl/data/ocha_hdx/oslo_accords_areas.shp \
    --version "HDX_2024-08-08" \
    --effective-date "1995-09-28" \
    --executed-by "your_username"
```

### 2. GeoMOLG - Master Plan Zoning

**Important:** GeoMOLG requires manual ArcGIS export. See [`etl/geomolg_etl_runbook.md`](etl/geomolg_etl_runbook.md) for detailed instructions.

```bash
# After manual export following runbook
python etl/import_geomolg.py \
    --file etl/data/geomolg/nablus_master_plan.shp \
    --version "GeoMOLG_2024-08-08" \
    --effective-date "2024-01-01" \
    --executed-by "your_username"
```

### 3. Comparable Sales (Comps)

Prepare a CSV with required columns:
- `latitude`, `longitude` (WGS84)
- `sale_date`, `price_ils`, `area_sqm`
- `locality`, `oslo_classification`

```bash
# Import comps (script TBD when data is available)
python etl/import_comps.py \
    --file etl/data/comps/nablus_comps_2024.csv \
    --version "Comps_2024-08-08"
```

## 🔧 Configuration

### Environment Variables

Edit `backend/.env`:

```bash
# Database
DATABASE_URL_SYNC=postgresql://landval:password@localhost:5432/landval_db
DATABASE_URL=postgresql+asyncpg://landval:password@localhost:5432/landval_db

# Security
SECRET_KEY=generate-a-secure-random-key-at-least-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440  # 24 hours

# CORS (comma-separated)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Phase 1 Configuration
ACTIVE_GOVERNORATE=Nablus

# Valuation Engine
CONFIDENCE_LEVEL=0.90
MIN_COMPS_FOR_REGRESSION=8
SHRINKAGE_SCALE_FACTOR=3.0
DEFAULT_COMP_RADIUS_M=3000
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## 📡 API Usage

### Authentication

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "full_name": "John Doe"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'
```

Response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true
  }
}
```

### Compute Valuation

```bash
curl -X POST http://localhost:8000/api/v1/valuation/compute \
  -H "Content-Type: application/json" \
  -d '{
    "latitude": 32.2211,
    "longitude": 35.2544,
    "area_sqm": 1000.0,
    "oslo_classification": "A",
    "distance_to_road_m": 150.0,
    "has_water_access": true,
    "has_electricity_access": true
  }'
```

Response:
```json
{
  "valuation_min_per_sqm": 180.50,
  "valuation_max_per_sqm": 245.30,
  "valuation_midpoint_per_sqm": 212.90,
  "valuation_confidence": 0.90,
  "comp_count": 23,
  "degrees_of_freedom": 15,
  "model_type": "shrinkage",
  "shrinkage_weight": 0.65,
  "valuation_date": "2026-08-08T10:30:00Z",
  "warnings": [],
  "disclaimer": "This valuation is an estimate, not an appraisal..."
}
```

### Interactive API Documentation

Visit http://localhost:8000/docs for Swagger UI with interactive testing.

## 🧪 Testing

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run valuation engine tests only
pytest tests/test_valuation_engine.py -v

# Run specific test
pytest tests/test_valuation_engine.py::TestShrinkageEstimator::test_shrinkage_weight_increases_with_comps
```

## 📁 Project Structure

```
Project-Price/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API routes
│   │   │   └── v1/            # Version 1 endpoints
│   │   │       ├── auth.py
│   │   │       ├── parcels.py
│   │   │       ├── users.py
│   │   │       └── valuation.py
│   │   ├── core/              # Core configuration
│   │   │   ├── config.py
│   │   │   ├── database.py
│   │   │   └── security.py
│   │   ├── models/            # SQLAlchemy ORM models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── valuation/         # Valuation engine
│   │   │   ├── engine.py
│   │   │   ├── models.py
│   │   │   └── README.md
│   │   └── main.py            # FastAPI app
│   ├── alembic/               # Database migrations
│   ├── tests/                 # Test suite
│   ├── scripts/               # Utility scripts
│   ├── pyproject.toml         # Dependencies
│   └── Dockerfile
├── etl/                       # ETL scripts
│   ├── import_ocha_hdx.py
│   ├── import_geomolg.py
│   ├── geomolg_etl_runbook.md
│   ├── common.py
│   └── README.md
├── docker-compose.yml
├── .env.example
├── .gitignore
└── README.md                  # This file
```

## 🔒 Security

### Privacy-by-Default

Per project blueprint:
- **Saved parcels are private** - No public activity feeds
- **User searches are confidential** - Reveal purchase intent
- **JWT tokens** - Stateless authentication, expire after 24 hours
- **Bcrypt password hashing** - Industry-standard security

### Best Practices

- **Never commit `.env` files** - Use `.env.example` as template
- **Rotate SECRET_KEY** regularly in production
- **Use HTTPS** in production (terminate SSL at reverse proxy)
- **Rate limit** API endpoints (implement in production)
- **Database backups** - Schedule automated backups

## 🎓 Valuation Methodology

### Hedonic Regression Model

The valuation engine implements a hedonic pricing model that estimates land value as a function of:

**Intrinsic Characteristics:**
- Parcel area (m²)
- Slope category (flat, moderate, steep)
- Zoning designation

**Extrinsic Characteristics:**
- Oslo classification (Area A, B, or C)
- Distance to nearest paved road
- Distance to city center
- Water infrastructure access
- Electricity infrastructure access

**Interaction Effects:**
- Road proximity × Oslo classification
- Infrastructure × Oslo classification

### Continuous Shrinkage Estimator

The engine uses a shrinkage estimator to prevent overreliance on sparse data:

```
w = min(1, N / (k × p))

Final Estimate = (1 - w) × Heuristic + w × Regression
```

Where:
- `N` = number of comparable sales
- `p` = number of model parameters (including interactions)
- `k` = scaling factor (default: 3.0)
- `w` = weight applied to regression (0 to 1)

**Result**: Smooth transition from heuristic baseline (when comps are scarce) to pure regression (when comps are abundant).

### Statistical Rigor

Per blueprint specifications:
- **T-distribution confidence intervals** with `N - p - 1` degrees of freedom
- **Residual degrees of freedom** properly tracked (not raw `N`)
- **90% confidence intervals** by default (configurable)
- **Ridge regression** with dynamic regularization

See [`backend/app/valuation/README.md`](backend/app/valuation/README.md) for mathematical details.

## 📜 Data Provenance

All spatial data includes mandatory provenance tracking:

| Field | Purpose |
|-------|---------|
| `source_version` | Dataset version identifier (e.g., "HDX_2024-08-08") |
| `effective_date` | Date when data became effective |
| `created_at` | Record creation timestamp |

**Why?** Stale geopolitical boundaries can result in severe financial miscalculations. The system tracks data vintage to prevent this.

All ETL operations are logged to `spatial_data_changelog` table for audit trail.

## ⚖️ Legal & Licensing

### Data Sources

**OCHA HDX (Oslo Accords Boundaries):**
- Source: UN Office for the Coordination of Humanitarian Affairs
- License: Open data (verify terms of use)

**GeoMOLG (Master Plans):**
- Source: Palestinian Ministry of Local Government
- **⚠️ CRITICAL**: Conduct legal review of Terms of Service before commercial use
- Current status: Academic pilot only (Phase 1)

### Disclaimer

Per blueprint requirement, all valuations include:

> "This valuation is an estimate, not an appraisal. Actual market values may differ. Consult a licensed appraiser for official valuations."

## 🗺️ Roadmap

### Phase 1: Nablus Governorate (Current)
- ✅ Backend API with valuation engine
- ✅ PostgreSQL + PostGIS database
- ✅ ETL pipeline for OCHA HDX and GeoMOLG
- ✅ User authentication and saved parcels
- ⏳ Frontend map interface (MapLibre GL)
- ⏳ Comparable sales data collection

### Phase 2: West Bank Expansion
- Expand to additional governorates (Ramallah, Bethlehem, Hebron, etc.)
- Enhanced spatial analysis (kriging, distance-decay weighting)
- Temporal price adjustment for historical comps
- Mobile-responsive design

### Phase 3: Advanced Features
- Machine learning ensemble models (Random Forest, XGBoost)
- User-contributed comps (with verification)
- Market trend analysis
- Historical price tracking
- API for third-party integration

## 🤝 Contributing

This is currently a pilot project for Nablus Governorate. Contributions welcome after Phase 1 completion.

### Development Setup

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run linter
ruff check .

# Format code
ruff format .

# Run tests with coverage
pytest --cov=app
```

## 📞 Contact

**Project Lead:** Omar Falah Rushdi Obeid  
**GitHub:** [@omob2022-commits](https://github.com/omob2022-commits)

## 📄 License

[To be determined]

## 🙏 Acknowledgments

- **OCHA HDX** for open geopolitical boundary data
- **Palestinian Ministry of Local Government** for master plan data (GeoMOLG)
- **OpenStreetMap** contributors for base map data
- **PostGIS** community for spatial database excellence

---

**Built with ❤️ for Palestine**

*Combating information asymmetry, one parcel at a time.*
