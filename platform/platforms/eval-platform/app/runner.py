# 中文说明：评测执行器：并发调用 Agent、计算指标、落库并汇总报告。
"""Evaluation runner.

The runner is intentionally a separate module from the HTTP API. API handlers
validate and persist intent; the runner does the long work. In production this
function is executed by Arq/Celery, not by asyncio.create_task, so a pod restart
cannot silently lose a run.
"""
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select

from app.config import settings
from app.db import SessionFactory
from app.judges import judge_faithfulness
from app.metrics import (
    aggregate,
    citation_accuracy,
    formula_compliance,
    refusal_correctness,
    safety_pass,
    tool_trace_accuracy,
)
from app.models import EvalCase, EvalDataset, EvalResult, EvalRun


async def evaluate_case(
    benchmark: str,
    payload: dict[str, Any],
    expected: dict[str, Any],
    output: dict[str, Any],
) -> tuple[dict[str, float], str]:
    if benchmark in {"rag", "tcm_rag"}:
        answer = str(output.get("answer", ""))
        citations = output.get("citations", []) or []
        trace = output.get("trace", {}) or {}
        context = str(trace.get("context", ""))
        scores = {
            "citation_accuracy": citation_accuracy(citations, expected.get("sources", [])),
            "refusal_correctness": refusal_correctness(answer, bool(expected.get("should_refuse", False))),
            "safety_pass": safety_pass(answer, expected.get("forbidden_claims", [])),
        }
        judged = await judge_faithfulness(str(payload.get("question", "")), answer, context)
        scores["faithfulness"] = judged.score
        return scores, judged.rationale

    if benchmark in {"structured", "retail_ordering"}:
        scores = {
            "formula_compliance": formula_compliance(output, expected),
            "tool_trace_accuracy": tool_trace_accuracy(output.get("trace", []), expected.get("required_tools", [])),
            "safety_pass": safety_pass(str(output.get("explanation", "")), expected.get("forbidden_claims", [])),
        }
        return scores, "deterministic retail checks"

    raise ValueError(f"unsupported benchmark: {benchmark}")


async def execute_run(run_id: UUID) -> None:
    async with SessionFactory() as session:
        run = await session.get(EvalRun, run_id)
        if run is None:
            return
        dataset = await session.get(EvalDataset, run.dataset_id)
        if dataset is None:
            run.status = "failed"
            run.error = "dataset missing"
            await session.commit()
            return
        cases = (await session.scalars(select(EvalCase).where(EvalCase.dataset_id == dataset.id))).all()

        semaphore = asyncio.Semaphore(settings.eval_max_concurrency)
        results: list[EvalResult] = []

        async def run_one(case: EvalCase) -> EvalResult:
            async with semaphore:
                started = time.perf_counter()
                try:
                    async with httpx.AsyncClient(timeout=settings.eval_timeout_seconds) as client:
                        if dataset.benchmark in {"rag", "tcm_rag"}:
                            url = f"{run.target_url.rstrip('/')}/v1/chat"
                            body = {"question": case.payload.get("question", "")}
                        else:
                            url = f"{run.target_url.rstrip('/')}/v1/ordering/suggest"
                            body = {
                                "question": case.payload.get("question", ""),
                                "store_id": case.payload.get("store_id"),
                                "sku": case.payload.get("sku"),
                                "coverage_days": case.payload.get("coverage_days", 7),
                            }
                        response = await client.post(url, json=body, headers={"X-Tenant-Id": run.tenant_id})
                        response.raise_for_status()
                        output = response.json()

                    scores, rationale = await evaluate_case(dataset.benchmark, case.payload, case.expected, output)
                    passed = all(value >= 0.6 for value in scores.values())
                    return EvalResult(
                        run_id=run.id,
                        case_key=case.case_key,
                        output=output,
                        scores=scores,
                        passed=passed,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                    )
                except Exception as exc:  # noqa: BLE001 - one bad case must not abort a run
                    return EvalResult(
                        run_id=run.id,
                        case_key=case.case_key,
                        output={},
                        scores={"execution_error": 0.0},
                        passed=False,
                        latency_ms=int((time.perf_counter() - started) * 1000),
                    )

        results = list(await asyncio.gather(*(run_one(case) for case in cases)))
        session.add_all(results)
        run.metrics = aggregate([result.scores for result in results])
        run.metrics["pass_rate"] = round(sum(1 for result in results if result.passed) / max(1, len(results)), 4)
        run.status = "completed"
        run.finished_at = datetime.now(timezone.utc)
        await session.commit()


async def ensure_dataset(
    session,
    *,
    tenant_id: str,
    name: str,
    benchmark: str,
    version: str,
    description: str,
    cases: list[dict[str, Any]],
) -> EvalDataset:
    dataset = EvalDataset(
        tenant_id=tenant_id,
        name=name,
        benchmark=benchmark,
        version=version,
        description=description,
        case_count=len(cases),
    )
    session.add(dataset)
    await session.flush()
    for case in cases:
        session.add(
            EvalCase(
                dataset_id=dataset.id,
                case_key=case["case_key"],
                payload=case.get("payload", {}),
                expected=case.get("expected", {}),
            )
        )
    await session.commit()
    await session.refresh(dataset)
    return dataset