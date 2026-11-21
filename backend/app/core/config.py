"""Backend configuration. All secrets come from the environment (backend/.env) — never from code."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BACKEND_DIR / ".env", env_file_encoding="utf-8", extra="ignore")

    # --- Infloww (read-only) ---
    infloww_api_key: SecretStr = Field(default=SecretStr(""))
    infloww_agency_oid: str = ""
    infloww_base_url: str = "https://openapi.infloww.com"
    infloww_platform_code: str = "OnlyFans"
    # Query-array serialisation. OpenAPI default (form/explode) => creatorIds=1&creatorIds=2.
    # "comma" => creatorIds=1,2. Verified against the live API by scripts/probe_api.py.
    infloww_array_style: str = "repeat"
    infloww_timeout_s: float = 30.0
    infloww_max_retries: int = 3
    # Agency limit is 1,000 QPM shared by ALL keys; stay well under it.
    infloww_qpm: int = 600
    infloww_concurrency: int = 6

    @field_validator("infloww_base_url")
    @classmethod
    def _strip_version(cls, v: str) -> str:
        # Spec paths already include /v1 (server is the bare host); avoid /v1/v1/... 404s.
        v = v.strip().rstrip("/")
        return v[:-3] if v.endswith("/v1") else v

    # --- Local storage ---
    database_path: Path = BACKEND_DIR / "data" / "agency.db"

    # --- Sync behaviour ---
    default_lookback_days: int = 30
    fan_history_days: int = 180          # history synced for fan LTV / segmentation (API max ~366)
    link_lookback_days: int = 365        # link listing window (links endpoint requires a time range)
    background_sync: bool = True
    background_interval_s: int = 900
    recent_ttl_s: int = 900              # re-fetch days within the unsettled window after this long
    settled_after_h: int = 30            # a UTC day is "settled" once fetched this long after it ended

    # Set ONLY by scripts/fixture_server.py. Surfaces a non-dismissable "FIXTURE DATA" banner in the UI.
    fixture_mode: bool = False

    # --- Dashboard API protection ---
    dashboard_access_token: SecretStr = Field(default=SecretStr(""))
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def configured(self) -> bool:
        return bool(self.infloww_api_key.get_secret_value() and self.infloww_agency_oid)

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
