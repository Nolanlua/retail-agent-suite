# 中文说明：LLM Judge 适配器：模型不可用时降级为离线启发式。
"""LLM judge adapters.

Judges are not ground truth. Every judge prompt asks for a bounded score and a
short rationale, and production dashboards show human agreement next to model
scores. If the model is unavailable, the runner degrades to a deterministic
heuristic rather than failing the whole batch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import httpx

from app.config import settings


@dataclass(frozen=True)
class JudgeResult:
    score: float
    rationale: str


async def judge_faithfulness(question: str, answer: str, context: str) -> JudgeResult:
    if not settings.llm_api_key:
        return _heuristic_faithfulness(answer, context)
    prompt = (
        "你是严格的中文 RAG 评审。只判断回答是否被给定资料支持。"
        "输出 JSON：score 为 0 到 1，rationale 不超过 40 字。"
        f"\n问题：{question}\n资料：{context[:6000]}\n回答：{answer[:3000]}"
    )
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.judge_model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            response.raise_for_status()
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            data = json.loads(content)
            return JudgeResult(score=float(data.get("score", 0)), rationale=str(data.get("rationale", "")))
    except Exception:  # noqa: BLE001 - eval must degrade, not crash
        return _heuristic_faithfulness(answer, context)


def _heuristic_faithfulness(answer: str, context: str) -> JudgeResult:
    # Cheap fallback for local runs: overlap of long Chinese tokens. This is not
    # a replacement for a judge; it only keeps the pipeline executable offline.
    import re

    tokens = set(re.findall(r"[\u4e00-\u9fff]{2,}", answer))
    if not tokens:
        return JudgeResult(score=0.0, rationale="回答为空或无有效中文片段")
    hit = sum(1 for token in tokens if token in context)
    score = min(1.0, hit / max(1, len(tokens)))
    return JudgeResult(score=round(score, 3), rationale="离线启发式：回答词片段与资料重合度")
