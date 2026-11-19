"""Retail API contracts."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SuggestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    store_id: str | None = None
    sku: str | None = None
    coverage_days: int = Field(default=7, ge=1, le=30)


class SupplierOut(BaseModel):
    supplier_code: str
    supplier_sku: str
    unit_price: float
    available_qty: int
    moq: int
    case_pack: int
    lead_time_days: int


class NoticeOut(BaseModel):
    slug: str
    title: str
    source: str
    content_md: str = ""


class ReminderOut(BaseModel):
    type: str
    severity: str
    title: str
    action: str
    source: str
    slug: str
    target_role: str


class SuggestionResponse(BaseModel):
    store_id: str
    sku: str
    target_date: str
    suggested_qty: int
    explanation: str
    forecast: dict[str, Any]
    risks: list[str]
    reasons: list[str]
    supplier: SupplierOut | None
    notices: list[NoticeOut]
    reminders: list[ReminderOut]
    trace: dict[str, Any]


class ConfirmRequest(BaseModel):
    store_id: str
    sku: str
    qty: int = Field(gt=0)
    supplier_code: str
    supplier_sku: str
    unit_price: float = Field(gt=0)
    idempotency_key: str | None = None


class ConfirmResponse(BaseModel):
    order_id: str
    status: str
    idempotent: bool = False