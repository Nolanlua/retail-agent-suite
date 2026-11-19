from app.domain.replenishment import ReplenishmentCalculator, ReplenishmentInput


def build_input(**overrides):
    values = dict(
        daily_qty=10,
        confidence=0.9,
        coverage_days=7,
        safety_days=2,
        on_hand=20,
        in_transit=10,
        moq=24,
        case_pack=12,
        available_qty=200,
        unit_price=9.5,
        budget=100000,
        max_order_qty=1000,
        shelf_life_days=180,
        lead_time_days=2,
    )
    values.update(overrides)
    return ReplenishmentInput(**values)


def test_basic_replenishment_is_60():
    result = ReplenishmentCalculator().calculate(build_input())
    assert result.suggested_qty == 60
    assert result.raw_gap == 60


def test_supplier_out_of_stock_returns_zero():
    result = ReplenishmentCalculator().calculate(build_input(available_qty=0))
    assert result.suggested_qty == 0
    assert "supplier_out_of_stock" in result.risks


def test_moq_rounds_up_to_case_pack():
    result = ReplenishmentCalculator().calculate(build_input(daily_qty=1, on_hand=0, in_transit=0, moq=30, case_pack=12))
    assert result.suggested_qty == 36
