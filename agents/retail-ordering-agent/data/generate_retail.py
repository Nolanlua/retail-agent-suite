# 中文说明：生成零食店/社区超市的模拟 SKU、销售、库存、促销和供应商报价。
"""Generate deterministic snack-store / supermarket data.

Outputs:
- data/local/dim_store.csv
- data/local/dim_sku.csv
- data/local/fact_sales.csv
- data/local/inventory_snapshot.csv
- data/local/promotions.csv
- data/local/supplier_offers.csv

The committed data/sample/sku_master.csv is a small, stable SKU dictionary for
code review and tests. The full local dataset is generated on demand.
"""
from __future__ import annotations

import csv
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / "data" / "local"
SAMPLE = ROOT / "data" / "sample"
LOCAL.mkdir(parents=True, exist_ok=True)
SAMPLE.mkdir(parents=True, exist_ok=True)

STORES = [f"S{index:02d}" for index in range(1, 9)]
CATEGORIES = ["饮料", "零食", "乳品", "日化", "粮油", "方便食品", "烘焙"]
START = "2026-08-01"


def build_sku_master() -> list[dict]:
    rng = random.Random(20261118)
    rows: list[dict] = []
    for index in range(1, 101):
        category = CATEGORIES[index % len(CATEGORIES)]
        rows.append(
            {
                "sku": f"SKU-{index:04d}",
                "sku_name": f"{category}商品{index:02d}",
                "category": category,
                "brand": f"品牌{index % 8 + 1}",
                "unit": "箱" if index % 3 == 0 else "件",
                "case_pack": [6, 12, 12, 24][index % 4],
                "moq": [12, 24, 24, 48][index % 4],
                "shelf_life_days": [90, 180, 365, 540][index % 4],
                "unit_price": round(rng.uniform(2.5, 39.0), 2),
            }
        )
    return rows


def build_stores() -> list[dict]:
    return [
        {
            "store_id": store,
            "store_name": f"演示门店{store[-1]}",
            "region": ["华北", "华东", "华南", "西南"][int(store[-1]) % 4],
            "store_type": "社区超市" if int(store[-1]) % 2 else "便利店",
        }
        for store in STORES
    ]


def build_sales(sku_rows: list[dict]) -> list[dict]:
    rng = random.Random(7)
    rows: list[dict] = []
    from datetime import date, timedelta

    start = date.fromisoformat(START)
    for store_index, store in enumerate(STORES):
        for sku_index, sku in enumerate(sku_rows):
            base = 5 + (sku_index % 13) * 1.7 + (store_index % 3) * 2
            for day_index in range(120):
                day = start + timedelta(days=day_index)
                weekday_factor = 1.2 if day.weekday() >= 5 else 1.0
                trend = 1.0 + day_index * 0.0012
                qty = max(0, round(base * weekday_factor * trend * rng.uniform(0.85, 1.15)))
                promo = 0
                if store_index == 0 and sku_index % 17 == 0 and 80 <= day_index <= 84:
                    promo = 1
                    qty = round(qty * 1.5)
                stockout = 1 if rng.random() < 0.012 else 0
                if stockout:
                    qty = 0
                rows.append(
                    {
                        "store_id": store,
                        "sku": sku["sku"],
                        "business_date": day.isoformat(),
                        "qty": qty,
                        "promo_flag": promo,
                        "stockout_flag": stockout,
                    }
                )
    return rows


def build_inventory(sku_rows: list[dict]) -> list[dict]:
    rng = random.Random(11)
    rows = []
    for store in STORES:
        for sku in sku_rows:
            rows.append(
                {
                    "store_id": store,
                    "sku": sku["sku"],
                    "on_hand": rng.randint(0, 120),
                    "in_transit": rng.randint(0, 60),
                    "safety_stock": rng.randint(6, 30),
                    "snapshot_date": "2026-11-18",
                }
            )
    return rows


def build_promotions(sku_rows: list[dict]) -> list[dict]:
    rows = []
    for index in range(18):
        rows.append(
            {
                "promo_id": f"P{index:03d}",
                "store_id": STORES[index % len(STORES)],
                "sku": sku_rows[index % len(sku_rows)]["sku"],
                "start_date": "2026-08-21",
                "end_date": "2026-08-25",
                "lift": round(1.3 + (index % 5) * 0.15, 2),
            }
        )
    return rows


def build_offers(sku_rows: list[dict]) -> list[dict]:
    rng = random.Random(99)
    rows = []
    for sku in sku_rows:
        for supplier in ["WY", "NANJING-WY", "LOCAL-01"]:
            rows.append(
                {
                    "supplier_code": supplier,
                    "sku": sku["sku"],
                    "supplier_sku": f"{supplier}-{sku['sku']}",
                    "available_qty": rng.choice([0, 24, 48, 96, 240, 480]),
                    "unit_price": round(sku["unit_price"] * rng.uniform(0.92, 1.08), 2),
                    "moq": sku["moq"],
                    "case_pack": sku["case_pack"],
                    "lead_time_days": rng.choice([1, 2, 3, 5, 7]),
                }
            )
    return rows


def write(name: str, rows: list[dict]) -> None:
    path = LOCAL / name
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print("wrote", path, len(rows))


def main() -> None:
    sku_rows = build_sku_master()
    write("dim_sku.csv", sku_rows)
    write("dim_store.csv", build_stores())
    write("fact_sales.csv", build_sales(sku_rows))
    write("inventory_snapshot.csv", build_inventory(sku_rows))
    write("promotions.csv", build_promotions(sku_rows))
    write("supplier_offers.csv", build_offers(sku_rows))
    with (SAMPLE / "sku_master.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(sku_rows[0].keys()))
        writer.writeheader()
        writer.writerows(sku_rows)


if __name__ == "__main__":
    main()