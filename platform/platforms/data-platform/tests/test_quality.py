"""Unit tests for quality rules that protect downstream agents."""
from __future__ import annotations

import pandas as pd
import pytest

from app.services.quality import RETAIL_SALES_SCHEMA, KNOWLEDGE_SCHEMA


def test_tcm_schema_accepts_valid_row() -> None:
    frame = pd.DataFrame(
        [
            {
                "doc_id": "tcm_1",
                "title": "黄芪条目",
                "category": "herb",
                "source": "药典",
                "content": "黄芪补气升阳。" * 20,
                "contraindications": ["阴虚阳亢者慎用"],
            }
        ]
    )
    KNOWLEDGE_SCHEMA.validate(frame)


def test_tcm_schema_rejects_short_content() -> None:
    frame = pd.DataFrame(
        [
            {
                "doc_id": "tcm_2",
                "title": "短文本",
                "category": "herb",
                "source": "药典",
                "content": "太短",
                "contraindications": [],
            }
        ]
    )
    with pytest.raises(Exception):
        KNOWLEDGE_SCHEMA.validate(frame, lazy=True)


def test_retail_sales_rejects_negative_quantity() -> None:
    frame = pd.DataFrame(
        [
            {
                "store_id": "S01",
                "sku": "SKU-0001",
                "business_date": "2026-08-01",
                "qty": -1,
                "promo_flag": 0,
            }
        ]
    )
    with pytest.raises(Exception):
        RETAIL_SALES_SCHEMA.validate(frame, lazy=True)
