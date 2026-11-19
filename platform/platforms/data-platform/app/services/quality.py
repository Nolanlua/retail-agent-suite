# 中文说明：数据质量规则：用 Pandera 校验文档、销售和库存数据，失败阻断发布。
"""Data quality checks.

Quality rules are code, reviewed like code and versioned with the pipeline. A
failed check blocks downstream publication; it never "logs and continues" for
golden datasets used by agents.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pandera.pandas as pa
from pandera.errors import SchemaErrors


KNOWLEDGE_SCHEMA = pa.DataFrameSchema(
    {
        "doc_id": pa.Column(str, unique=True, nullable=False),
        "title": pa.Column(str, pa.Check.str_length(min_value=2), nullable=False),
        "category": pa.Column(str, pa.Check.isin(["classic", "herb", "formula", "guideline"]), nullable=False),
        "source": pa.Column(str, nullable=False),
        "content": pa.Column(str, pa.Check.str_length(min_value=80), nullable=False),
        "dynasty": pa.Column(str, nullable=True, required=False),
        "herbs": pa.Column(object, nullable=True, required=False),
        "formulas": pa.Column(object, nullable=True, required=False),
        "contraindications": pa.Column(object, nullable=True, required=False),
    },
    strict=True,
    coerce=True,
)

RETAIL_SALES_SCHEMA = pa.DataFrameSchema(
    {
        "store_id": pa.Column(str, nullable=False),
        "sku": pa.Column(str, nullable=False),
        "business_date": pa.Column(pa.DateTime, nullable=False),
        "qty": pa.Column(int, pa.Check.ge(0), nullable=False),
        "promo_flag": pa.Column(int, pa.Check.isin([0, 1]), nullable=False),
        "stockout_flag": pa.Column(int, pa.Check.isin([0, 1]), nullable=True, required=False),
    },
    strict=True,
    coerce=True,
)

RETAIL_INVENTORY_SCHEMA = pa.DataFrameSchema(
    {
        "store_id": pa.Column(str, nullable=False),
        "sku": pa.Column(str, nullable=False),
        "on_hand": pa.Column(int, pa.Check.ge(0), nullable=False),
        "in_transit": pa.Column(int, pa.Check.ge(0), nullable=False),
        "snapshot_date": pa.Column(pa.DateTime, nullable=False),
        "safety_stock": pa.Column(int, pa.Check.ge(0), nullable=True, required=False),
    },
    strict=True,
    coerce=True,
)


def _read_uri(uri: str) -> pd.DataFrame:
    path = Path(uri)
    if not path.exists():
        raise FileNotFoundError(f"quality input not found: {uri}")
    if path.suffix == ".jsonl":
        return pd.read_json(path, lines=True)
    if path.suffix in {".csv"}:
        return pd.read_csv(path)
    if path.suffix in {".parquet"}:
        return pd.read_parquet(path)
    raise ValueError(f"unsupported quality input: {path.suffix}")


def _validate(schema: pa.DataFrameSchema, frame: pd.DataFrame) -> dict[str, Any]:
    try:
        schema.validate(frame, lazy=True)
        return {"checked_rows": len(frame), "failed_rows": 0, "failures": []}
    except SchemaErrors as exc:
        cases = exc.failure_cases.head(50).to_dict(orient="records")
        failed = len(exc.failure_cases)
        return {"checked_rows": len(frame), "failed_rows": failed, "failures": cases}


def _extra_knowledge_checks(frame: pd.DataFrame) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    duplicate_sources = frame[frame.duplicated(subset=["source", "title"], keep=False)]
    for _, row in duplicate_sources.head(20).iterrows():
        failures.append({"check": "duplicate_source_title", "doc_id": row["doc_id"]})
    return {"failed_rows": len(duplicate_sources), "failures": failures}


async def run_quality(ruleset: str, uri: str) -> dict[str, Any]:
    """Run a named ruleset against a URI and return an operator-friendly report."""
    frame = _read_uri(uri)
    if ruleset == "knowledge_documents":
        result = _validate(KNOWLEDGE_SCHEMA, frame)
        extra = _extra_knowledge_checks(frame)
        result["failed_rows"] += extra["failed_rows"]
        result["failures"].extend(extra["failures"])
    elif ruleset == "retail_sales":
        result = _validate(RETAIL_SALES_SCHEMA, frame)
        duplicates = frame.duplicated(subset=["store_id", "sku", "business_date"]).sum()
        result["failed_rows"] += int(duplicates)
        if duplicates:
            result["failures"].append({"check": "duplicate_store_sku_day", "count": int(duplicates)})
    elif ruleset == "retail_inventory":
        result = _validate(RETAIL_INVENTORY_SCHEMA, frame)
    else:
        raise ValueError(f"unknown ruleset: {ruleset}")

    result["ruleset"] = ruleset
    result["source"] = uri
    return result