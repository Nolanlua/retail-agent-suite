"""Service configuration loaded from environment variables.

Environment variables are the contract between deployment and code. Secrets
never ship in the repository; local values live in .env and production values
come from a secret manager.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Service identity is used by logs, traces and eval records.
    service_name: str = Field(default="agent-service")
    app_env: Literal["local", "test", "staging", "prod"] = "local"
    log_level: str = "INFO"

    # Shared infrastructure. All values are injected; nothing is hard-coded.
    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
    redis_url: str = "redis://localhost:6379/0"

    # Auth: every public request carries a JWT. Internal service calls may use
    # a short-lived service token instead of a user token.
    jwt_secret: str = "replace-me"
    jwt_algorithm: str = "HS256"
    jwt_audience: str = "agent-platform"
    tenant_header: str = "X-Tenant-Id"
    internal_service_token: str = "internal-token"

    # Downstream addresses are configuration, not code constants, so the same
    # image can run in local, staging and production.
    data_platform_url: str = "http://localhost:8001"
    eval_platform_url: str = "http://localhost:8002"
    order_service_url: str = "http://localhost:8020"

    # Observability is optional locally but mandatory in production.
    otel_exporter_otlp_endpoint: str = ""
    langfuse_host: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""

    # Upstream timeouts are deliberately explicit. In production, a request
    # without a timeout is treated as an incident waiting to happen.
    http_timeout_seconds: float = 8.0
    http_connect_timeout_seconds: float = 2.0


@lru_cache
def get_settings() -> Settings:
    """Return one immutable settings object per process."""
    return Settings()
