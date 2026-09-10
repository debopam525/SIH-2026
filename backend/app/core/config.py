"""Central configuration. All settings are environment-overridable (prefix ``ECDAT_``)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
APP_DIR = BACKEND_DIR / "app"
DATA_DIR = APP_DIR / "data"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ECDAT_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    env: str = "dev"
    database_url: str = f"sqlite+pysqlite:///{BACKEND_DIR / 'ecdat.db'}"

    jwt_secret: str = "dev-only-secret-change-me-change-me-change-me"
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_minutes: int = 1440

    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )

    scan_workdir: Path = BACKEND_DIR / ".ecdat_work"
    reports_dir: Path = BACKEND_DIR / "reports_out"

    log_level: str = "INFO"
    log_json: bool = False

    # Analysis assumption: years until a cryptographically-relevant quantum computer (CRQC).
    # This is an ASSUMPTION, not a prediction. Commonly cited industry estimates cluster around
    # 10-20 years; ECDAT defaults to 15. Editable at runtime in Settings (admin only).
    crqc_horizon_years: int = 15

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, v: object) -> object:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    s = get_settings_uncached()
    return s


def get_settings_uncached() -> Settings:
    s = Settings()
    s.scan_workdir.mkdir(parents=True, exist_ok=True)
    s.reports_dir.mkdir(parents=True, exist_ok=True)
    return s


settings = get_settings()
