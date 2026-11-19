"""公告对补货建议的确定性影响。

召回是硬规则：目标 SKU 必须建议 0；陈列/价格/新品只生成提醒，
不直接修改计算出的补货量，避免 LLM 或公告文本随意改数字。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class NoticeImpact:
    blocked_skus: set[str] = field(default_factory=set)
    reminders: list[dict] = field(default_factory=list)
    notice_unavailable: bool = False


def apply_notices(sku: str, notices: list[dict]) -> NoticeImpact:
    impact = NoticeImpact()
    for notice in notices:
        text = f"{notice.get('title', '')}\n{notice.get('content_md', '')}"
        title = str(notice.get("title", ""))
        source = str(notice.get("source", ""))
        slug = str(notice.get("slug", ""))
        sku_mentioned = sku in text
        if "召回" in title or "召回" in text[:200]:
            if sku_mentioned or "全部" in title:
                impact.blocked_skus.add(sku)
                impact.reminders.append(
                    {
                        "type": "recall",
                        "severity": "urgent",
                        "title": f"商品召回：{title}",
                        "action": "立即下架、停止订货并登记自查",
                        "source": source,
                        "slug": slug,
                        "target_role": "store-manager",
                    }
                )
        elif "陈列" in title or "端头" in title:
            impact.reminders.append(
                {
                    "type": "display_change",
                    "severity": "important",
                    "title": title,
                    "action": "按公告调整端头陈列，并在系统登记完成时间",
                    "source": source,
                    "slug": slug,
                    "target_role": "store-manager",
                }
            )
        elif "价格" in title:
            impact.reminders.append(
                {
                    "type": "price_change",
                    "severity": "important",
                    "title": title,
                    "action": "核对最新供货价和系统零售价，不得自行改价",
                    "source": source,
                    "slug": slug,
                    "target_role": "category-specialist",
                }
            )
        elif "新品" in title:
            impact.reminders.append(
                {
                    "type": "new_product",
                    "severity": "normal",
                    "title": title,
                    "action": "按新品上架要求完成首铺和首周动销复盘",
                    "source": source,
                    "slug": slug,
                    "target_role": "store-manager",
                }
            )
    return impact


def extract_sku(text: str) -> list[str]:
    return re.findall(r"SKU-\d{4}", text)
