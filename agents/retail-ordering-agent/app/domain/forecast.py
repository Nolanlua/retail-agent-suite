# 中文说明：需求预测：7/28 天加权、趋势、促销和置信度。
"""Demand forecast for a store/SKU pair.

This is an explainable baseline, not a black-box model. It is intentionally
conservative and can be replaced by a trained model later as long as the output
contract stays the same.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class ForecastResult:
    daily_qty: float
    baseline: float
    trend_factor: float
    promo_factor: float
    confidence: float
    sample_note: str


class DemandForecaster:
    def forecast(self, features: dict[str, Any], target_date: date, promo_lift: float = 0.0) -> ForecastResult:
        avg_7 = float(features.get("avg_qty_7d") or 0.0)
        avg_28 = float(features.get("avg_qty_28d") or avg_7)
        baseline = avg_7 if avg_7 > 0 else avg_28

        if avg_28 <= 0:
            trend = 1.0
        else:
            trend = max(0.8, min(1.3, (avg_7 + 0.5) / (avg_28 + 0.5)))

        promo_factor = 1.0 + max(-0.8, promo_lift)
        daily = max(0.0, baseline * trend * promo_factor)
        confidence = self._confidence(avg_7, avg_28, promo_lift)

        note = "近 7 天与 28 天销售均可用" if avg_28 > 0 and avg_7 > 0 else "历史样本不足，已降级为保守估计"
        return ForecastResult(
            daily_qty=round(daily, 2),
            baseline=round(baseline, 2),
            trend_factor=round(trend, 4),
            promo_factor=round(promo_factor, 4),
            confidence=confidence,
            sample_note=note,
        )

    @staticmethod
    def _confidence(avg_7: float, avg_28: float, promo_lift: float) -> float:
        if avg_7 <= 0 or avg_28 <= 0:
            return 0.35
        volatility = abs(avg_7 - avg_28) / max(avg_28, 0.1)
        confidence = max(0.1, min(1.0, 0.9 - volatility * 0.4))
        if promo_lift:
            confidence *= 0.9
        return round(confidence, 3)
