from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "recipient-extract-api"
    redis_url: str = "redis://localhost:6379/0"
    redis_key_prefix: str = "recipient:extract:v1:"
    redis_ttl_seconds: int = 24 * 60 * 60

    openai_api_key: str = Field(default="test-key", alias="OPENAI_API_KEY")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_model_text: str = "qwen-vl-max-latest"
    openai_model_image: str = "qwen-vl-max-latest"
    openai_timeout_seconds: float = 60.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
