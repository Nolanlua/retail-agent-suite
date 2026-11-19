"""Retail agent configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class RetailSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "retail-ordering-agent"
    app_env: str = "local"
    log_level: str = "INFO"

    data_platform_url: str = "http://localhost:8001"
    knowledge_agent_url: str = "http://localhost:8011"
    order_service_url: str = "http://localhost:8020"
    order_service_token: str = "internal-token"
    internal_service_token: str = "internal-token"

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"

    default_coverage_days: int = 7
    default_safety_days: int = 2
    max_order_qty: int = 1000
    request_timeout_seconds: float = 20.0


settings = RetailSettings()