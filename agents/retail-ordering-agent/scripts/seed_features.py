# 中文说明：把模拟数据汇总成补货特征并写入数据中台。
"""Build and POST feature snapshots to the data platform.

Run after data/generate_retail.py and after the data platform is reachable.
This script intentionally computes features with plain Python; in production the
same definitions live in dbt and are published by the ingestion DAG.
"""
from __future__ import annotations

import csv
import json
import os
import urllib.request
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "data" / "local"
BASE = os.getenv("DATA_PLATFORM_URL", "http://localhost:8001")
TOKEN = os.getenv("INTERNAL_SERVICE_TOKEN", "internal-token")
TENANT = os.getenv("DEMO_TENANT_ID", "demo")


def read_csv(name: str) -> list[dict]:
    with (LOCAL / name).open(encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    sku = {row["sku"]: row for row in read_csv("dim_sku.csv")}
    inventory = {(row["store_id"], row["sku"]): row for row in read_csv("inventory_snapshot.csv")}
    sales: dict[tuple[str, str], list[int]] = defaultdict(list)
    for row in read_csv("fact_sales.csv"):
        if row["stockout_flag"] == "0":
            sales[(row["store_id"], row["sku"])].append(int(row["qty"]))

    points = []
    for (store, sku_code), values in sales.items():
        avg7 = sum(values[-7:]) / max(1, len(values[-7:]))
        avg28 = sum(values[-28:]) / max(1, len(values[-28:]))
        inv = inventory.get((store, sku_code), {})
        master = sku[sku_code]
        points.append(
            {
                "feature_view": "feature_replenishment_input",
                "entity_key": f"{store}:{sku_code}",
                "business_date": "2026-11-18T00:00:00Z",
                "version": "v1",
                "payload": {
                    "avg_qty_7d": round(avg7, 2),
                    "avg_qty_28d": round(avg28, 2),
                    "on_hand": int(inv.get("on_hand", 0)),
                    "in_transit": int(inv.get("in_transit", 0)),
                    "safety_stock": int(inv.get("safety_stock", 0)),
                    "case_pack": int(master["case_pack"]),
                    "moq": int(master["moq"]),
                    "shelf_life_days": int(master["shelf_life_days"]),
                    "unit_price": float(master["unit_price"]),
                },
            }
        )

    for point in points:
        req = urllib.request.Request(
            f"{BASE}/v1/features/snapshot",
            data=json.dumps(point).encode(),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "X-Tenant-Id": TENANT,
                "X-Internal-Token": TOKEN,
            },
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read()
    print("seeded", len(points), "feature points")


if __name__ == "__main__":
    main()
