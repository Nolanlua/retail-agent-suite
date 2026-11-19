"""Evaluation platform configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class EvalSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "eval-platform"
    app_env: str = "local"
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/agent_platform"
    internal_service_token: str = "internal-token"
    eval_max_concurrency: int = 4
    eval_timeout_seconds: float = 60.0
    judge_model: str = "gpt-4.1-mini"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""


settings = EvalSettings()
