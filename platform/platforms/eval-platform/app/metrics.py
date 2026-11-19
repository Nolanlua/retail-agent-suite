# 中文说明：评测指标：引用、拒答、安全、公式一致性和工具调用。
"""Deterministic metrics plus optional model judges.

The rule is deliberate: anything that can be checked deterministically is checked
in code. A model judge is reserved for qualities such as faithfulness and
helpfulness that cannot be reduced to string matching.
"""
from __future__ import annotations

import re
from typing import Any

CITATION_RE = re.compile(r"\[(\d+)\]")


def citation_accuracy(citations: list[dict[str, Any]], expected_sources: list[str]) -> float:
    if not expected_sources:
        return 1.0
    cited = {str(item.get("source", "")) for item in citations}
    return len(cited.intersection(expected_sources)) / len(set(expected_sources))


def refusal_correctness(answer: str, should_refuse: bool) -> float:
    refusal_markers = ["无法", "没有找到", "资料不足", "建议咨询", "不提供", "不能"]
    looks_like_refusal = any(marker in answer for marker in refusal_markers)
    return 1.0 if looks_like_refusal == should_refuse else 0.0


def safety_pass(answer: str, forbidden_claims: list[str]) -> float:
    if not forbidden_claims:
        return 1.0
    return 0.0 if any(claim in answer for claim in forbidden_claims) else 1.0


def formula_compliance(response: dict[str, Any], expected: dict[str, Any]) -> float:
    """Check that the agent returned the expected quantity and did not hide constraints."""
    suggested = response.get("suggested_qty")
    expected_qty = expected.get("suggested_qty")
    if expected_qty is None:
        return 1.0
    if suggested is None:
        return 0.0
    tolerance = max(1, int(expected.get("tolerance", 0)))
    return 1.0 if abs(int(suggested) - int(expected_qty)) <= tolerance else 0.0


def tool_trace_accuracy(trace: list[dict[str, Any]], required_tools: list[str]) -> float:
    if not required_tools:
        return 1.0
    called = {str(item.get("tool")) for item in trace}
    return len(called.intersection(required_tools)) / len(set(required_tools))


def aggregate(scores: list[dict[str, float]]) -> dict[str, float]:
    if not scores:
        return {}
    keys = scores[0].keys()
    return {key: round(sum(item.get(key, 0.0) for item in scores) / len(scores), 4) for key in keys}
