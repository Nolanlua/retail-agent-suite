"""retail knowledge agent configuration."""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class KnowledgeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    service_name: str = "retail-knowledge-agent"
    app_env: str = "local"
    log_level: str = "INFO"
    agent_port: int = 8011
    database_url: str = "postgresql+asyncpg://agent:agent@localhost:5432/retail_knowledge"
    wiki_index_on_approval: bool = True

    data_platform_url: str = "http://localhost:8001"
    eval_platform_url: str = "http://localhost:8002"
    internal_service_token: str = "internal-token"

    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "retail_knowledge_chunks"
    opensearch_url: str = "http://localhost:9200"
    opensearch_index: str = "retail_knowledge_docs"
    neo4j_url: str = "http://localhost:7474"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j123"

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4.1-mini"
    embedding_model: str = "text-embedding-3-large"
    embedding_dim: int = 3072

    top_k: int = 8
    bm25_top_k: int = 30
    vector_top_k: int = 30
    rrf_k: int = 60
    max_rewrite_queries: int = 3
    request_timeout_seconds: float = 30.0


settings = KnowledgeSettings()