"""
Valuation engine implementing hedonic regression with shrinkage estimator.

Per blueprint specifications:
1. Hedonic regression model with interaction effects
2. Continuous shrinkage estimator (Ridge regression with weighted multiplier)
3. T-distribution confidence intervals with N-p-1 degrees of freedom
4. Smooth transition from heuristic baseline to pure regression as N grows
"""

from datetime import datetime, timezone
from typing import Optional

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from app.core.config import settings
from app.valuation.models import ValuationRequest, ValuationResult, CompData


class ValuationEngine:
    """Land valuation engine with hedonic regression and shrinkage.
    
    Implements the continuous shrinkage estimator to smoothly transition
    from heuristic baseline (when N is small) to pure regression (when N is large).
    
    Formula: w = min(1, N / (k * p))
    where:
        - N = number of comps
        - p = number of parameters (including interaction terms)
        - k = scaling factor (from config, default 3.0)
        - w = weight applied to regression (0 to 1)
    
    Final estimate: (1 - w) * heuristic + w * regression
    """
    
    def __init__(self):
        """Initialize valuation engine."""
        self.confidence_level = settings.confidence_level
        self.min_comps_for_regression = settings.min_comps_for_regression
        self.shrinkage_scale_factor = settings.shrinkage_scale_factor
    
    def compute_valuation(
        self,
        request: ValuationRequest,
        comps: list[CompData]
    ) -> ValuationResult:
        """Compute land valuation with confidence interval.
        
        Args:
            request: Valuation request with parcel features
            comps: List of comparable sales
        
        Returns:
            ValuationResult with range and metadata
        """
        warnings = []
        comp_count = len(comps)
        
        # Case 1: No comps available - use heuristic baseline only
        if comp_count == 0:
            return self._heuristic_only_valuation(request, warnings)
        
        # Case 2: Try regression with shrinkage (let DoF check handle insufficiency)
        return self._shrinkage_regression_valuation(request, comps, warnings)
    
    def _heuristic_only_valuation(
        self,
        request: ValuationRequest,
        warnings: list[str]
    ) -> ValuationResult:
        """Compute valuation using heuristic baseline only.
        
        Used when no comps are available.
        
        Args:
            request: Valuation request
            warnings: List to append warnings to
        
        Returns:
            ValuationResult using heuristic baseline
        """
        # Use unified heuristic computation
        heuristic_price = self._compute_heuristic_baseline(request)
        
        # Wide confidence interval (±50%) due to lack of data
        margin = heuristic_price * 0.5
        
        warnings.append(
            "Heuristic baseline only - no comparable sales data available. "
            "Valuation has high uncertainty."
        )
        
        return ValuationResult(
            valuation_min_per_sqm=max(0, heuristic_price - margin),
            valuation_max_per_sqm=heuristic_price + margin,
            valuation_confidence=0.50,  # Low confidence
            comp_count=0,
            degrees_of_freedom=0,
            model_type="heuristic",
            shrinkage_weight=0.0,
            valuation_date=datetime.now(timezone.utc),
            warnings=warnings,
        )
    
    def _shrinkage_regression_valuation(
        self,
        request: ValuationRequest,
        comps: list[CompData],
        warnings: list[str]
    ) -> ValuationResult:
        """Compute valuation using hedonic regression with shrinkage.
        
        Implements continuous shrinkage estimator that smoothly transitions
        from heuristic baseline to pure regression as N grows.
        
        Args:
            request: Valuation request
            comps: List of comparable sales
            warnings: List to append warnings to
        
        Returns:
            ValuationResult with shrinkage-adjusted estimate
        """
        # Prepare feature matrix and target vector
        X_train, y_train = self._prepare_training_data(comps)
        X_pred = self._prepare_prediction_features(request)
        
        # Count parameters (including interaction terms)
        n_params = X_train.shape[1]
        n_comps = len(comps)
        
        # Compute shrinkage weight
        # w = min(1, N / (k * p))
        shrinkage_weight = min(1.0, n_comps / (self.shrinkage_scale_factor * n_params))
        
        # Compute degrees of freedom: N - p - 1
        # Per blueprint: "must strictly apply a T-distribution against the 
        # computed N - p - 1 residual degrees of freedom"
        degrees_of_freedom = n_comps - n_params - 1
        
        if degrees_of_freedom <= 0:
            warnings.append(
                f"Insufficient degrees of freedom ({degrees_of_freedom}). "
                f"Need at least {n_params + 2} comps for regression with {n_params} parameters."
            )
            return self._heuristic_only_valuation(request, warnings)
        
        # Standardize features for Ridge regression
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_pred_scaled = scaler.transform(X_pred)
        
        # Fit Ridge regression with alpha responsive to shrinkage weight
        # Higher shrinkage weight (more data) = lower regularization (trust data more)
        # Lower shrinkage weight (less data) = higher regularization (regularize more)
        alpha = max(0.1, 2.0 * (1.0 - shrinkage_weight))
        model = Ridge(alpha=alpha)
        model.fit(X_train_scaled, y_train)
        
        # Predict price
        y_pred_regression = model.predict(X_pred_scaled)[0]
        
        # Compute heuristic baseline
        heuristic_price = self._compute_heuristic_baseline(request)
        
        # Apply shrinkage: blend heuristic and regression
        y_pred_final = (1 - shrinkage_weight) * heuristic_price + shrinkage_weight * y_pred_regression
        
        # Compute residual standard error
        y_pred_train = model.predict(X_train_scaled)
        residuals = y_train - y_pred_train
        residual_std_error = np.sqrt(np.sum(residuals**2) / degrees_of_freedom)
        
        # Compute confidence interval using T-distribution
        # Per blueprint: use T-distribution with N-p-1 degrees of freedom
        t_critical = stats.t.ppf((1 + self.confidence_level) / 2, degrees_of_freedom)
        
        # Standard error of prediction (accounts for both sampling error and new prediction)
        # SE = s * sqrt(1 + 1/N + (x - x_mean)^T * (X^T X)^-1 * (x - x_mean))
        # Simplified approximation: SE ≈ s * sqrt(1 + 1/N)
        standard_error = residual_std_error * np.sqrt(1 + 1 / n_comps)
        
        # Margin of error
        margin = t_critical * standard_error
        
        # Final confidence interval
        valuation_min = max(0, y_pred_final - margin)
        valuation_max = y_pred_final + margin
        
        # Add warning if shrinkage weight is low
        if shrinkage_weight < 0.5:
            warnings.append(
                f"Shrinkage weight is {shrinkage_weight:.2f} - valuation heavily weighted "
                f"toward heuristic baseline due to limited comp data."
            )
        
        # Add warning if confidence interval is very wide
        if (valuation_max - valuation_min) / y_pred_final > 0.8:
            warnings.append(
                "Wide confidence interval (>80% of midpoint) indicates high uncertainty. "
                "More comp data would improve precision."
            )
        
        return ValuationResult(
            valuation_min_per_sqm=valuation_min,
            valuation_max_per_sqm=valuation_max,
            valuation_confidence=self.confidence_level,
            comp_count=n_comps,
            degrees_of_freedom=degrees_of_freedom,
            model_type="shrinkage" if shrinkage_weight < 1.0 else "regression",
            shrinkage_weight=shrinkage_weight,
            valuation_date=datetime.now(timezone.utc),
            warnings=warnings,
        )
    
    def _prepare_training_data(
        self,
        comps: list[CompData]
    ) -> tuple[np.ndarray, np.ndarray]:
        """Prepare feature matrix and target vector from comp data.
        
        Includes interaction effects per blueprint specification.
        
        Args:
            comps: List of comparable sales
        
        Returns:
            Tuple of (X_train, y_train)
        """
        features = []
        targets = []
        
        for comp in comps:
            feature_vec = self._extract_features(
                oslo_classification=comp.oslo_classification,
                distance_to_road_m=comp.distance_to_road_m,
                distance_to_city_center_m=comp.distance_to_city_center_m,
                has_water_access=comp.has_water_access,
                has_electricity_access=comp.has_electricity_access,
                slope_category=comp.slope_category,
            )
            features.append(feature_vec)
            targets.append(comp.price_per_sqm)
        
        return np.array(features), np.array(targets)
    
    def _prepare_prediction_features(
        self,
        request: ValuationRequest
    ) -> np.ndarray:
        """Prepare feature vector for prediction.
        
        Args:
            request: Valuation request
        
        Returns:
            Feature vector as 2D array (1 row)
        """
        feature_vec = self._extract_features(
            oslo_classification=request.oslo_classification,
            distance_to_road_m=request.distance_to_road_m,
            distance_to_city_center_m=request.distance_to_city_center_m,
            has_water_access=request.has_water_access,
            has_electricity_access=request.has_electricity_access,
            slope_category=request.slope_category,
        )
        return np.array([feature_vec])
    
    def _extract_features(
        self,
        oslo_classification: str,
        distance_to_road_m: Optional[float],
        distance_to_city_center_m: Optional[float],
        has_water_access: Optional[bool],
        has_electricity_access: Optional[bool],
        slope_category: Optional[str],
    ) -> list[float]:
        """Extract feature vector from parcel characteristics.
        
        Implements hedonic pricing model with interaction effects.
        Per blueprint: "road proximity impacting value differently in Area C vs. Area A"
        
        Args:
            oslo_classification: Area classification
            distance_to_road_m: Distance to road (optional)
            distance_to_city_center_m: Distance to city center (optional)
            has_water_access: Water availability (optional)
            has_electricity_access: Electricity availability (optional)
            slope_category: Terrain classification (optional)
        
        Returns:
            Feature vector
        """
        features = []
        
        # Oslo classification (one-hot encoding)
        features.append(1.0 if oslo_classification == "A" else 0.0)
        features.append(1.0 if oslo_classification == "B" else 0.0)
        features.append(1.0 if oslo_classification == "C" else 0.0)
        
        # Distance features (log-transformed for non-linear effects)
        road_dist = distance_to_road_m if distance_to_road_m is not None else 500.0
        city_dist = distance_to_city_center_m if distance_to_city_center_m is not None else 5000.0
        
        features.append(np.log1p(road_dist))  # log(1 + x) for numerical stability
        features.append(np.log1p(city_dist))
        
        # Infrastructure access (binary)
        features.append(1.0 if has_water_access else 0.0)
        features.append(1.0 if has_electricity_access else 0.0)
        
        # Slope category (one-hot encoding)
        slope = slope_category or "flat"
        features.append(1.0 if slope == "flat" else 0.0)
        features.append(1.0 if slope == "moderate" else 0.0)
        features.append(1.0 if slope == "steep" else 0.0)
        
        # Interaction effects (per blueprint specification)
        # Road proximity × Oslo classification
        is_area_a = 1.0 if oslo_classification == "A" else 0.0
        is_area_c = 1.0 if oslo_classification == "C" else 0.0
        
        features.append(is_area_a * np.log1p(road_dist))  # Area A × road distance
        features.append(is_area_c * np.log1p(road_dist))  # Area C × road distance
        
        # Infrastructure × Oslo classification
        has_water = 1.0 if has_water_access else 0.0
        features.append(is_area_a * has_water)  # Area A × water access
        
        return features
    
    def _compute_heuristic_baseline(self, request: ValuationRequest) -> float:
        """Compute heuristic baseline price estimate.
        
        Unified heuristic used for both heuristic-only and shrinkage blending.
        
        Args:
            request: Valuation request
        
        Returns:
            Baseline price in ₪/m²
        """
        # Base heuristic: median land value in Palestine (rough estimate)
        # This should be calibrated with actual market data
        base_price = 150.0  # ₪/m² baseline
        
        # Oslo classification multipliers
        oslo_multipliers = {
            "A": 1.0,
            "B": 0.7,
            "C": 0.3,
        }
        
        multiplier = oslo_multipliers.get(request.oslo_classification, 0.5)
        
        # Adjust for infrastructure
        if request.has_water_access:
            multiplier *= 1.2
        if request.has_electricity_access:
            multiplier *= 1.15
        
        # Adjust for road proximity
        if request.distance_to_road_m is not None and request.distance_to_road_m < 100:
            multiplier *= 1.1
        
        return base_price * multiplier
