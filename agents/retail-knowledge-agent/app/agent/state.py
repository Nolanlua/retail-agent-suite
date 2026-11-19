"""State shared by every node in the retail knowledge graph.

Fields are grouped by stage so an operator reading a trace can tell which node
produced a value. The state is intentionally plain data; no database handles or
unserializable clients live here.
"""
from __future__ import annotations

from typing import Any, TypedDict


class KnowledgeState(TypedDict, total=False):
    question: str
    conversation_id: str
    tenant_id: str
    history: list[dict[str, str]]

    intent: str
    normalized_terms: list[str]
    rewritten_queries: list[str]

    candidates: list[dict[str, Any]]
    graph_facts: list[list[Any]]
    context: str
    citations: list[dict[str, Any]]

    safety_level: str
    safety_reasons: list[str]
    disclaimer: str

    answer: str
    validation: dict[str, Any]
    error: str
    trace: dict[str, Any]