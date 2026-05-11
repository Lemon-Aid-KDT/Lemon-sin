"""애플리케이션 설정."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경 변수 기반 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    environment: Literal["development", "staging", "production"] = "development"
    log_level: str = Field(default="INFO")

    # DB (Phase 1 후반부터 사용)
    database_url: str = Field(default="postgresql+asyncpg://lemon:lemon@localhost:5432/lemon")
    redis_url: str = Field(default="redis://localhost:6379/0")

    # External APIs (Phase 2부터 사용, 현재는 선택)
    anthropic_api_key: SecretStr | None = Field(default=None)
    google_application_credentials: str | None = Field(default=None)
    mfds_api_key: SecretStr | None = Field(default=None)


@lru_cache
def get_settings() -> Settings:
    """설정 싱글턴.

    Returns:
        애플리케이션 설정 (lru_cache로 1회만 로드).
    """
    return Settings()
