from datetime import date

from app.domain.forecast import DemandForecaster


def test_forecast_uses_recent_baseline() -> None:
    result = DemandForecaster().forecast(
        {"avg_qty_7d": 12, "avg_qty_28d": 10},
        target_date=date(2026, 12, 7),
        promo_lift=0.0,
    )
    assert result.daily_qty > 10
    assert result.confidence > 0


def test_forecast_without_history_is_low_confidence() -> None:
    result = DemandForecaster().forecast({}, target_date=date(2026, 12, 7))
    assert result.daily_qty == 0
    assert result.confidence == 0.35
