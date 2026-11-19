"""Eval platform API contracts."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class CaseInput(BaseModel):
    case_key: str
    payload: dict[str, Any]
    expected: dict[str, Any] = Field(default_factory=dict)


class DatasetCreate(BaseModel):
    name: str
    benchmark: Literal["rag", "structured"]
    version: str = "v1"
    description: str = ""
    cases: list[CaseInput] = Field(min_length=1)


class DatasetOut(BaseModel):
    id: UUID
    tenant_id: str
    name: str
    benchmark: str
    version: str
    case_count: int
    created_at: datetime


class RunCreate(BaseModel):
    dataset_id: UUID
    target_name: str
    target_url: str


class RunOut(BaseModel):
    id: UUID
    status: str
    target_name: str
    metrics: dict[str, Any]
    error: str
    started_at: datetime
    finished_at: datetime | None


class CaseScore(BaseModel):
    case_key: str
    passed: bool
    scores: dict[str, float]
    rationale: str = ""