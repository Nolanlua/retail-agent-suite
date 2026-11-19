# 中文说明：补货公式与约束：箱规、MOQ、可供货量、预算和最大订货量。
"""Replenishment calculation and business constraints.

Formula:
    forecast_demand = daily_qty * coverage_days
    safety_stock = daily_qty * safety_days
    raw_gap = forecast_demand + safety_stock - on_hand - in_transit

The result is then constrained by case pack, MOQ, supplier availability, budget
and max order quantity. Every adjustment is recorded in risks/reasons so the
store manager can audit the recommendation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil


@dataclass(frozen=True)
class ReplenishmentInput:
    daily_qty: float
    confidence: float
    coverage_days: int
    safety_days: int
    on_hand: int
    in_transit: int
    moq: int
    case_pack: int
    available_qty: int
    unit_price: float
    budget: float
    max_order_qty: int
    shelf_life_days: int
    lead_time_days: int


@dataclass
class ReplenishmentResult:
    suggested_qty: int
    forecast_demand: float
    safety_stock: float
    raw_gap: float
    risks: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def _round_to_case(qty: int, case_pack: int) -> int:
    if case_pack <= 1:
        return qty
    return int(ceil(qty / case_pack) * case_pack)


class ReplenishmentCalculator:
    def calculate(self, data: ReplenishmentInput) -> ReplenishmentResult:
        forecast_demand = round(data.daily_qty * data.coverage_days, 2)
        safety_stock = round(data.daily_qty * data.safety_days, 2)
        raw_gap = forecast_demand + safety_stock - data.on_hand - data.in_transit
        risks: list[str] = []
        reasons: list[str] = []

        if raw_gap <= 0:
            return ReplenishmentResult(
                suggested_qty=0,
                forecast_demand=forecast_demand,
                safety_stock=safety_stock,
                raw_gap=round(raw_gap, 2),
                risks=["overstock_risk"],
                reasons=["现有库存与在途库存已覆盖预测需求和安全库存"],
            )

        qty = _round_to_case(int(ceil(raw_gap)), data.case_pack)
        reasons.append(f"原始缺口 {raw_gap:.1f}，按箱规 {data.case_pack} 向上取整为 {qty}")

        if qty < data.moq:
            qty = _round_to_case(data.moq, data.case_pack)
            reasons.append(f"低于 MOQ {data.moq}，调整为 {qty}")

        if data.available_qty <= 0:
            return ReplenishmentResult(
                suggested_qty=0,
                forecast_demand=forecast_demand,
                safety_stock=safety_stock,
                raw_gap=round(raw_gap, 2),
                risks=["supplier_out_of_stock"],
                reasons=["供应商可供货量为 0，建议转人工或换供应商"],
            )
        if qty > data.available_qty:
            qty = (data.available_qty // max(1, data.case_pack)) * data.case_pack
            risks.append("supplier_limited")
            reasons.append(f"按可供货量 {data.available_qty} 截断")

        if qty > data.max_order_qty:
            qty = (data.max_order_qty // max(1, data.case_pack)) * data.case_pack
            risks.append("max_order_capped")
            reasons.append(f"按单店最大订货量 {data.max_order_qty} 截断")

        if data.unit_price > 0 and data.budget > 0:
            affordable = int(data.budget // data.unit_price)
            affordable = (affordable // max(1, data.case_pack)) * data.case_pack
            if qty > affordable:
                qty = affordable
                risks.append("budget_limited")
                reasons.append(f"按预算 {data.budget:.0f} 元截断")

        if data.shelf_life_days and data.coverage_days + data.lead_time_days > data.shelf_life_days:
            risks.append("shelf_life_risk")
        if data.confidence < 0.6:
            risks.append("low_forecast_confidence")
        if qty <= 0:
            risks.append("no_order_after_constraints")

        return ReplenishmentResult(
            suggested_qty=max(0, qty),
            forecast_demand=forecast_demand,
            safety_stock=safety_stock,
            raw_gap=round(raw_gap, 2),
            risks=risks,
            reasons=reasons,
        )
