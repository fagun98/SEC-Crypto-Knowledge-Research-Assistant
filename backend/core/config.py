from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "SEC Crypto AI Assistant API"
    api_prefix: str = "/api"
    frontend_url: str = "http://localhost:3000"
    reports_dir: Path = Field(default=Path("weekly_reports"))
    openai_llm_model: str = "gpt-4o-mini"

    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", PROJECT_ROOT / "backend" / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def resolved_reports_dir(self) -> Path:
        path = self.reports_dir
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()
