# Valuation Engine

The valuation engine is the core algorithmic component of the Palestine Land Valuation platform. It computes land price estimates using hedonic regression with a continuous shrinkage estimator.

## Overview

The engine implements three key features per the project blueprint:

1. **Hedonic Regression Model** - Models land value as a function of intrinsic and extrinsic characteristics
2. **Continuous Shrinkage Estimator** - Smoothly transitions from heuristic baseline to pure regression as data grows
3. **T-Distribution Confidence Intervals** - Accounts for small sample sizes using proper statistical inference

## Mathematical Foundation

### Hedonic Pricing Model

Land value is modeled as:

```
Price = β₀ + β₁X₁ + β₂X₂ + ... + βₙXₙ + ε
```

Where:
- `X₁, X₂, ..., Xₙ` = parcel characteristics (Oslo area, road distance, infrastructure, etc.)
- `β₁, β₂, ..., βₙ` = coefficients estimated from comparable sales
- `ε` = error term

### Interaction Effects

Per blueprint specification, the model includes interaction terms to capture non-linear relationships:

- **Road Proximity × Oslo Classification** - Road access has different value impacts in Area A vs Area C
- **Infrastructure × Oslo Classification** - Water/electricity access matters more in certain areas

Example interaction term:
```
β_interaction = β_road_area_a × (IsAreaA × log(RoadDistance))
```

### Continuous Shrinkage Estimator

The shrinkage estimator blends heuristic baseline with regression prediction:

```
Final Estimate = (1 - w) × Heuristic + w × Regression
```

Where the shrinkage weight `w` is computed as:

```
w = min(1, N / (k × p))
```

- `N` = number of comparable sales
- `p` = number of model parameters (including interaction terms)
- `k` = scaling factor (default: 3.0, from config)

**Rationale**: When comps are scarce (N is small), the model relies more on the heuristic baseline. As N grows, it smoothly transitions to pure regression, preventing discontinuous "jumps" in valuations.

### Degrees of Freedom

Per blueprint specification, confidence intervals must account for the number of parameters:

```
DOF = N - p - 1
```

This is the **residual degrees of freedom** used for T-distribution lookups, not raw `N`.

**Critical**: Using `N` instead of `N - p - 1` would underestimate uncertainty, especially when interaction terms are included.

### Confidence Intervals

The valuation range is computed using the T-distribution:

```
Margin = t(α/2, DOF) × SE
```

Where:
- `t(α/2, DOF)` = critical value from T-distribution with DOF degrees of freedom
- `SE` = standard error of prediction
- `α` = 1 - confidence_level (default: 0.10 for 90% confidence)

Final range:
```
[Price - Margin, Price + Margin]
```

## Feature Engineering

### Input Features

The model uses the following parcel characteristics:

| Feature | Type | Transformation | Description |
|---------|------|----------------|-------------|
| Oslo Classification | Categorical | One-hot encoding | Area A, B, or C |
| Road Distance | Continuous | log(1 + x) | Distance to nearest paved road (meters) |
| City Center Distance | Continuous | log(1 + x) | Distance to governorate capital (meters) |
| Water Access | Binary | 0 or 1 | Water infrastructure availability |
| Electricity Access | Binary | 0 or 1 | Electricity infrastructure availability |
| Slope Category | Categorical | One-hot encoding | Flat, moderate, or steep |

### Feature Scaling

Features are standardized using `StandardScaler` before regression:

```
X_scaled = (X - μ) / σ
```

This ensures all features contribute equally to the model regardless of their native scale.

## Model Types

The engine returns one of three model types based on data availability:

### 1. Heuristic Only (`model_type="heuristic"`)

**When**: No comps or fewer than `min_comps_for_regression`

**Method**: Simple rule-based multipliers based on Oslo classification

**Confidence**: Low (50%)

**Range**: ±50% of estimate

### 2. Shrinkage (`model_type="shrinkage"`)

**When**: Sufficient comps but `w < 1.0`

**Method**: Blend of heuristic and regression weighted by shrinkage factor

**Confidence**: Configured level (default 90%)

**Range**: T-distribution based on actual data

### 3. Pure Regression (`model_type="regression"`)

**When**: Many comps and `w = 1.0`

**Method**: Pure regression without heuristic component

**Confidence**: Configured level (default 90%)

**Range**: T-distribution based on actual data

## Usage

### Basic Example

```python
from app.valuation import ValuationEngine, ValuationRequest, CompData
from datetime import datetime, timezone

# Initialize engine
engine = ValuationEngine()

# Create valuation request
request = ValuationRequest(
    latitude=32.2211,
    longitude=35.2544,
    area_sqm=1000.0,
    oslo_classification="A",
    distance_to_road_m=150.0,
    has_water_access=True,
    has_electricity_access=True,
)

# Fetch comps from database (example)
comps = [
    CompData(
        price_per_sqm=250.0,
        area_sqm=1200.0,
        oslo_classification="A",
        distance_to_road_m=100.0,
        sale_date=datetime(2024, 1, 15, tzinfo=timezone.utc),
    ),
    # ... more comps ...
]

# Compute valuation
result = engine.compute_valuation(request, comps)

print(f"Valuation Range: ₪{result.valuation_min_per_sqm:.2f} - ₪{result.valuation_max_per_sqm:.2f} per m²")
print(f"Confidence: {result.valuation_confidence * 100}%")
print(f"Model Type: {result.model_type}")
print(f"Comps Used: {result.comp_count}")
print(f"Degrees of Freedom: {result.degrees_of_freedom}")
print(f"Shrinkage Weight: {result.shrinkage_weight:.2f}")

for warning in result.warnings:
    print(f"⚠️  {warning}")
```

### Configuration

The engine reads configuration from `app.core.config.Settings`:

```python
# backend/.env
CONFIDENCE_LEVEL=0.90  # 90% confidence intervals
MIN_COMPS_FOR_REGRESSION=8  # Minimum comps to use regression
SHRINKAGE_SCALE_FACTOR=3.0  # k in w = min(1, N / (k * p))
DEFAULT_COMP_RADIUS_M=3000.0  # Search radius for comps (3 km)
```

## Testing

The valuation engine has comprehensive test coverage per blueprint requirement:

> "Strict test coverage is required for the valuation engine to prevent silent regressions in financial outputs."

Run tests:

```bash
cd backend
pytest tests/test_valuation_engine.py -v
```

Test categories:
- **Heuristic Baseline** - Verifies rule-based estimates
- **Shrinkage Estimator** - Tests weight formula and transitions
- **Degrees of Freedom** - Validates DOF = N - p - 1
- **Confidence Intervals** - Tests T-distribution calculations
- **Interaction Effects** - Verifies hedonic model structure
- **Edge Cases** - Tests error handling and warnings

## Warnings System

The engine returns warnings for data quality issues:

| Warning | Trigger | Recommendation |
|---------|---------|----------------|
| "no comparable sales data available" | 0 comps | Collect market transaction data |
| "Only N comps available (minimum M recommended)" | N < min threshold | Increase comp data coverage |
| "Insufficient degrees of freedom" | DOF ≤ 0 | Reduce model complexity or add comps |
| "Shrinkage weight is X - heavily weighted toward heuristic" | w < 0.5 | Add more comp data |
| "Wide confidence interval (>80% of midpoint)" | Large uncertainty | Data has high variance, need more comps |

## Future Enhancements

Potential improvements for Phase 2+:

1. **Temporal Adjustment** - Adjust historical comps for time-based price changes
2. **Spatial Kriging** - Weight nearby comps more heavily using distance-decay
3. **Ensemble Methods** - Combine multiple regression models (Ridge, Lasso, Random Forest)
4. **Automated Feature Selection** - Use LASSO to identify most important features
5. **Calibration** - Compare predictions to actual sales and recalibrate
6. **Uncertainty Decomposition** - Separate model uncertainty from data uncertainty

## References

- **Hedonic Pricing**: Rosen, S. (1974). "Hedonic Prices and Implicit Markets"
- **Shrinkage Estimation**: Stein, C. (1956). "Inadmissibility of the Usual Estimator"
- **Ridge Regression**: Hoerl & Kennard (1970). "Ridge Regression: Biased Estimation for Nonorthogonal Problems"
- **Small Sample Inference**: Student (1908). "The Probable Error of a Mean"

## See Also

- [`models.py`](./models.py) - Data models for requests/results
- [`engine.py`](./engine.py) - Core valuation logic
- [`../../tests/test_valuation_engine.py`](../../tests/test_valuation_engine.py) - Test suite
- [Project Blueprint](../../../README.md) - Full system specification
