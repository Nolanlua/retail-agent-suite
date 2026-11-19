"""Request and response contracts for the data platform."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    domain: Literal["knowledge", "retail", "shared"]
    asset_type: Literal["document_corpus", "table", "feature_view", "knowledge_graph"]
    storage_uri: str
    owner: str
    sensitivity: Literal["public", "internal", "confidential"] = "internal"
    description: str = ""


class AssetOut(BaseModel):
    id: UUID
    tenant_id: str
    name: str
    domain: str
    asset_type: str
    owner: str
    version: int
    created_at: datetime


class QualityRunRequest(BaseModel):
    asset_id: UUID
    ruleset: Literal["knowledge_documents", "retail_sales", "retail_inventory"]
    sample_uri: str = Field(description="Object-store URI or local path used for the check")


class QualityRunOut(BaseModel):
    id: UUID
    status: str
    checked_rows: int
    failed_rows: int
    report: dict[str, Any]


class FeatureQuery(BaseModel):
    feature_view: str = "feature_replenishment_input"
    store_id: str
    sku: str
    business_date: datetime


class FeaturePoint(BaseModel):
    entity_key: str
    business_date: datetime
    version: str
    payload: dict[str, Any]


class FeatureSnapshotWrite(BaseModel):
    feature_view: str
    entity_key: str
    business_date: datetime
    version: str = "v1"
    payload: dict[str, Any]


class LineageOut(BaseModel):
    upstream: str
    downstream: str
    job_name: str
    created_at: datetime
