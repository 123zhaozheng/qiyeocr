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

    ftp_host: str = Field(default="", alias="FTP_HOST")
    ftp_port: int = Field(default=21, alias="FTP_PORT")
    ftp_username: str | None = Field(default=None, alias="FTP_USERNAME")
    ftp_password: str | None = Field(default=None, alias="FTP_PASSWORD")
    ftp_base_dir: str | None = Field(default=None, alias="FTP_BASE_DIR")
    ftp_timeout_seconds: float = Field(default=30.0, alias="FTP_TIMEOUT_SECONDS")
    ftp_passive: bool = Field(default=True, alias="FTP_PASSIVE")
    ftp_use_tls: bool = Field(default=False, alias="FTP_USE_TLS")
    ftp_encoding: str = Field(default="utf-8", alias="FTP_ENCODING")


@lru_cache
def get_settings() -> Settings:
    return Settings()
