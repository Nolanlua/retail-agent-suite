"""Metric tests are cheap and catch the most embarrassing regressions."""
from __future__ import annotations

from app.metrics import citation_accuracy, formula_compliance, refusal_correctness, safety_pass


def test_citation_accuracy_handles_subset() -> None:
    citations = [{"source": "中国药典"}, {"source": "方剂学"}]
    assert citation_accuracy(citations, ["中国药典"]) == 1.0


def test_refusal_detection() -> None:
    assert refusal_correctness("资料不足，无法回答，建议咨询医师", True) == 1.0
    assert refusal_correctness("黄芪可以补气", False) == 1.0


def test_safety_blocks_forbidden_claim() -> None:
    assert safety_pass("可以自行加大剂量", ["自行加大剂量"]) == 0.0
    assert safety_pass("请遵医嘱", ["自行加大剂量"]) == 1.0


def test_formula_compliance_tolerance() -> None:
    assert formula_compliance({"suggested_qty": 60}, {"suggested_qty": 60}) == 1.0
    assert formula_compliance({"suggested_qty": 48}, {"suggested_qty": 60},) == 0.0
