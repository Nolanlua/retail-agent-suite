# 中文说明：连锁零售知识库的合规预检：价格承诺、召回绕过、内部资料外发和供应商底价泄露。
"""Rule-first compliance guard for an internal retail knowledge base.

The assistant serves store managers and company specialists. It must not promise
prices, bypass a recall, or leak internal documents. These rules are simple,
auditable and independent of the LLM.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ComplianceDecision:
    level: str
    reasons: list[str] = field(default_factory=list)
    disclaimer: str = (
        "以上内容来自公司内部知识库，仅供授权员工执行参考；"
        "价格、召回、陈列和促销以系统公告及负责人最终确认为准。"
    )


PRICE_PATTERNS = [
    r"保证最低价|全网最低|价格随便改|绕过价格审批",
]
RECALL_PATTERNS = [
    r"召回.*(继续卖|不上报|不撤架|偷偷卖)|已经被召回.*(还能卖|怎么卖)",
]
INTERNAL_PATTERNS = [
    r"内部文件.*(外发|发给客户|发到群里)|供应商底价.*(发|告诉)|员工.*(身份证|电话|工资).*发",
]
SUPPLIER_CONFIDENTIAL_PATTERNS = [
    r"南京万优.*底价|供应商.*返点.*(告诉|发)",
]


class ComplianceGuard:
    def evaluate(self, question: str, intent: str = "") -> ComplianceDecision:
        reasons: list[str] = []
        if any(re.search(pattern, question) for pattern in PRICE_PATTERNS):
            reasons.append("price_commitment")
        if any(re.search(pattern, question) for pattern in RECALL_PATTERNS):
            reasons.append("recall_bypass")
        if any(re.search(pattern, question) for pattern in INTERNAL_PATTERNS):
            reasons.append("internal_document_leak")
        if any(re.search(pattern, question) for pattern in SUPPLIER_CONFIDENTIAL_PATTERNS):
            reasons.append("supplier_confidential")
        if reasons:
            return ComplianceDecision(level="block", reasons=reasons)
        return ComplianceDecision(level="pass")

    def inspect_answer(self, answer: str) -> list[str]:
        forbidden = [
            r"保证最低价",
            r"全网最低",
            r"召回商品可以继续销售",
            r"内部文件可以外发",
            r"供应商底价可以公开",
            r"不用上报",
        ]
        return [pattern for pattern in forbidden if re.search(pattern, answer)]
