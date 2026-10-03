"""Konfigurasi aplikasi yang dibaca dari environment (lihat .env.example)."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# backend/sentinel/config.py -> root repo ada dua tingkat di atas paket.
_ROOT_REPO = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ROOT_REPO / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinel"
    anthropic_api_key: SecretStr | None = None
    anthropic_model: str = "claude-sonnet-5"
    demo_mode: bool = False
    parameter_path: Path = _ROOT_REPO / "config" / "parameter.yaml"


@lru_cache
def get_settings() -> Settings:
    return Settings()
