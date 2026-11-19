"""retail knowledge agent API contracts."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    conversation_id: str | None = Field(default=None, max_length=64)
    history: list[dict[str, str]] = Field(default_factory=list, max_length=20)


class CitationOut(BaseModel):
    index: int
    doc_id: str
    chunk_id: str
    title: str
    source: str
    section: str = ""
    snippet: str = ""


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    citations: list[CitationOut]
    intent: str
    safety: str
    latency_ms: int
    trace: dict[str, Any]


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    top_k: int = Field(default=8, ge=1, le=20)


class SearchHit(BaseModel):
    chunk_id: str
    doc_id: str
    title: str
    source: str
    text: str
    score: float

class NoticeOut(BaseModel):
    slug: str
    title: str
    source: str
    content_md: str
    updated_at: Any
