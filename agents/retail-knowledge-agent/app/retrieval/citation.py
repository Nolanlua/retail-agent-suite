# 中文说明：引用编号生成和越界校验。
"""Citation assembly and validation.

The model never creates citation numbers. Code assigns [1]..[n] in retrieval
order, and code verifies every number after generation. This is the difference
between "looks cited" and "auditable".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CITATION_PATTERN = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class CitationReport:
    valid_indexes: list[int]
    invalid_indexes: list[int]
    citation_count: int

    @property
    def valid(self) -> bool:
        return self.citation_count > 0 and not self.invalid_indexes


class CitationBuilder:
    def build(self, chunks: list[Any]) -> tuple[str, list[dict[str, Any]]]:
        blocks: list[str] = []
        citations: list[dict[str, Any]] = []
        for index, chunk in enumerate(chunks, start=1):
            blocks.append(
                f"[{index}] 文档：{chunk.title}；来源：{chunk.source}；章节：{chunk.section}\n{chunk.text}"
            )
            citations.append(
                {
                    "index": index,
                    "doc_id": chunk.doc_id,
                    "chunk_id": chunk.chunk_id,
                    "title": chunk.title,
                    "source": chunk.source,
                    "section": chunk.section,
                    "snippet": chunk.text[:260],
                }
            )
        return "\n\n".join(blocks), citations

    def validate(self, answer: str, citations: list[dict[str, Any]]) -> CitationReport:
        indexes = [int(value) for value in CITATION_PATTERN.findall(answer)]
        upper = len(citations)
        valid = sorted({index for index in indexes if 1 <= index <= upper})
        invalid = sorted({index for index in indexes if index < 1 or index > upper})
        return CitationReport(valid_indexes=valid, invalid_indexes=invalid, citation_count=len(indexes))


def fallback_answer(citations: list[dict[str, Any]]) -> str:
    if not citations:
        return "知识库暂未找到足够证据回答这个问题。请补充更具体的病名、症状或药材名称，或咨询执业零售师。"
    first = citations[0]
    return (
        f"知识库暂未生成可靠回答。根据检索到的资料《{first['title']}》（{first['source']}），"
        "建议先核对原文和适用范围。[1] 具体执行以公司系统和负责人确认为准。"
    )