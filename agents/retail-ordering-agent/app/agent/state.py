"""State shared by the retail ordering graph."""
from __future__ import annotations

from typing import Any, TypedDict


class OrderingState(TypedDict, total=False):
    question: str
    tenant_id: str
    store_id: str
    sku: str
    target_date: str
    coverage_days: int

    features: dict[str, Any]
    forecast: dict[str, Any]
    offers: list[dict[str, Any]]
    notices: list[dict[str, Any]]
    reminders: list[dict[str, Any]]
    selected_offer: dict[str, Any] | None
    suggestion: dict[str, Any]
    explanation: str
    error: str
    trace: dict[str, Any]