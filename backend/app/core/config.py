"""
Application configuration via Pydantic Settings.

Reads from environment variables or .env file. All sensitive values
(DB credentials, secret keys) must be provided externally — never hardcoded.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Land Valuation API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ─── Database ───────────────────────────────────────
    database_url: str = (
        "postgresql+asyncpg://landval:changeme@localhost:5432/landval_db"
    )
    database_url_sync: str = (
        "postgresql://landval:changeme@localhost:5432/landval_db"
    )

    # ─── Security ──────────────────────────────────────
    secret_key: str = "INSECURE-DEV-KEY-CHANGE-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440  # 24 hours

    # ─── CORS ──────────────────────────────────────────
    cors_origins: str = "http://localhost:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    # ─── Phase Config ─────────────────────────────────
    active_governorate: str = "Nablus"

    # ─── Valuation Engine ─────────────────────────────
    default_comp_radius_m: float = 3000.0  # 3 km
    min_comps_for_regression: int = 8
    confidence_level: float = 0.90
    shrinkage_scale_factor: float = 3.0  # k in w = min(1, N / (k * p))


settings = Settings()
