"""Chat application service.

The service owns composition and request lifecycle. Nodes stay pure orchestration
functions, which makes them easy to unit test and reason about.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.agent.graph import build_graph
from app.agent.state import KnowledgeState
from app.retrieval.retriever import KnowledgeRetriever
from app.safety.guard import ComplianceGuard


@dataclass
class ChatResult:
    answer: str
    citations: list[dict[str, Any]] = field(default_factory=list)
    intent: str = ""
    safety: str = "pass"
    trace: dict[str, Any] = field(default_factory=dict)
    latency_ms: int = 0


class ChatService:
    def __init__(self) -> None:
        self._retriever = KnowledgeRetriever()
        self._safety = ComplianceGuard()
        self._graph = build_graph(self._retriever, self._safety)

    async def ask(
        self,
        *,
        question: str,
        tenant_id: str,
        conversation_id: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        started = time.perf_counter()
        thread_id = conversation_id or f"retail-knowledge-{uuid.uuid4().hex[:12]}"
        state: KnowledgeState = {
            "question": question,
            "tenant_id": tenant_id,
            "conversation_id": thread_id,
            "history": history or [],
            "trace": {"thread_id": thread_id},
        }
        result = await self._graph.ainvoke(
            state,
            config={"configurable": {"thread_id": thread_id}, "recursion_limit": 8},
        )
        trace = dict(result.get("trace", {}))
        # Evaluation needs the exact context used for the answer. Truncate it in
        # the API response to avoid leaking the entire corpus to clients.
        trace["context"] = str(result.get("context", ""))[:6000]
        return ChatResult(
            answer=str(result.get("answer", "")),
            citations=list(result.get("citations", [])),
            intent=str(result.get("intent", "")),
            safety=str(result.get("safety_level", "pass")),
            trace=trace,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
