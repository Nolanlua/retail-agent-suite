"""Data platform configuration."""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataPlatformSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "data-platform"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minio"
    s3_secret_key: str = "minio123"
    s3_bucket: str = "agent-platform"
    internal_service_token: str = "internal-token"
    feature_max_staleness_hours: int = Field(default=72, ge=1)


settings = DataPlatformSettings()
