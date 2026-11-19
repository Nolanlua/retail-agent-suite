"""Ordering application service."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from app.agent.graph import build_graph
from app.agent.state import OrderingState
from app.clients.order_service import OrderServiceClient


@dataclass
class SuggestionResult:
    store_id: str
    sku: str
    target_date: str
    suggested_qty: int
    explanation: str
    forecast: dict[str, Any] = field(default_factory=dict)
    risks: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    supplier: dict[str, Any] | None = None
    notices: list[dict[str, Any]] = field(default_factory=list)
    reminders: list[dict[str, Any]] = field(default_factory=list)
    trace: dict[str, Any] = field(default_factory=dict)


class OrderingService:
    def __init__(self) -> None:
        self._graph = build_graph()
        self._orders = OrderServiceClient()

    async def suggest(
        self,
        *,
        question: str,
        tenant_id: str,
        store_id: str | None = None,
        sku: str | None = None,
        coverage_days: int = 7,
    ) -> SuggestionResult:
        started = time.perf_counter()
        state: OrderingState = {
            "question": question,
            "tenant_id": tenant_id,
            "store_id": store_id or "",
            "sku": sku or "",
            "coverage_days": coverage_days,
            "trace": {"request_id": uuid.uuid4().hex},
        }
        result = await self._graph.ainvoke(
            state,
            config={"configurable": {"thread_id": uuid.uuid4().hex}, "recursion_limit": 8},
        )
        suggestion = result.get("suggestion", {})
        trace = dict(result.get("trace", {}))
        trace["latency_ms"] = int((time.perf_counter() - started) * 1000)
        trace["features"] = result.get("features", {})
        trace["offers"] = result.get("offers", [])
        return SuggestionResult(
            store_id=result.get("store_id", ""),
            sku=result.get("sku", ""),
            target_date=result.get("target_date", ""),
            suggested_qty=int(suggestion.get("suggested_qty", 0)),
            explanation=str(result.get("explanation", "")),
            forecast=result.get("forecast", {}),
            risks=list(suggestion.get("risks", [])),
            reasons=list(suggestion.get("reasons", [])),
            supplier=result.get("selected_offer"),
            notices=list(result.get("notices", [])),
            reminders=list(result.get("reminders", [])),
            trace=trace,
        )

    async def confirm(
        self,
        *,
        tenant_id: str,
        store_id: str,
        sku: str,
        qty: int,
        supplier_code: str,
        supplier_sku: str,
        unit_price: float,
        operator: str,
        idempotency_key: str,
    ) -> dict[str, Any]:
        payload = {
            "store_id": store_id,
            "sku": sku,
            "qty": qty,
            "supplier_code": supplier_code,
            "supplier_sku": supplier_sku,
            "unit_price": unit_price,
            "operator": operator,
        }
        return await self._orders.create_order(tenant_id, payload, idempotency_key)