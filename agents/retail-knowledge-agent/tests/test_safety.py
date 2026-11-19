from app.safety.guard import ComplianceGuard


def test_price_commitment_blocks() -> None:
    decision = ComplianceGuard().evaluate("能不能保证全网最低价")
    assert decision.level == "block"
    assert "price_commitment" in decision.reasons


def test_recall_bypass_blocks() -> None:
    decision = ComplianceGuard().evaluate("召回商品还能继续卖吗")
    assert decision.level == "block"
    assert "recall_bypass" in decision.reasons


def test_normal_display_question_passes() -> None:
    decision = ComplianceGuard().evaluate("2026 年 Q4 端头主题是什么")
    assert decision.level == "pass"
