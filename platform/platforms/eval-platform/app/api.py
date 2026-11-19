# 中文说明：评测中台 API：数据集版本、评测任务和单条结果。
"""HTTP API for datasets, runs and reports."""
from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_common.errors import AppError
from app.db import get_session
from app.models import EvalDataset, EvalResult, EvalRun
from app.runner import ensure_dataset, execute_run
from app.schemas import CaseScore, DatasetCreate, DatasetOut, RunCreate, RunOut

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "eval-platform"}


@router.post("/v1/datasets", response_model=DatasetOut, status_code=201)
async def create_dataset(
    payload: DatasetCreate,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    session: AsyncSession = Depends(get_session),
) -> DatasetOut:
    dataset = await ensure_dataset(
        session,
        tenant_id=tenant_id,
        name=payload.name,
        benchmark=payload.benchmark,
        version=payload.version,
        description=payload.description,
        cases=[case.model_dump() for case in payload.cases],
    )
    return DatasetOut.model_validate(dataset)


@router.get("/v1/datasets", response_model=list[DatasetOut])
async def list_datasets(
    tenant_id: str = Header(alias="X-Tenant-Id"),
    session: AsyncSession = Depends(get_session),
) -> list[DatasetOut]:
    rows = (
        await session.scalars(
            select(EvalDataset).where(EvalDataset.tenant_id == tenant_id).order_by(desc(EvalDataset.created_at))
        )
    ).all()
    return [DatasetOut.model_validate(row) for row in rows]


@router.post("/v1/runs", response_model=RunOut, status_code=202)
async def create_run(
    payload: RunCreate,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    session: AsyncSession = Depends(get_session),
) -> RunOut:
    dataset = await session.get(EvalDataset, payload.dataset_id)
    if dataset is None or dataset.tenant_id != tenant_id:
        raise AppError("dataset_not_found", "dataset not found", 404)

    run = EvalRun(
        tenant_id=tenant_id,
        dataset_id=dataset.id,
        target_name=payload.target_name,
        target_url=payload.target_url,
        status="queued",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    # Local convenience. Replace with a durable queue in staging/production.
    asyncio.create_task(execute_run(run.id))
    return RunOut.model_validate(run)


@router.get("/v1/runs/{run_id}", response_model=RunOut)
async def get_run(
    run_id: UUID,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    session: AsyncSession = Depends(get_session),
) -> RunOut:
    run = await session.get(EvalRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise AppError("run_not_found", "run not found", 404)
    return RunOut.model_validate(run)


@router.get("/v1/runs/{run_id}/results", response_model=list[CaseScore])
async def get_results(
    run_id: UUID,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    session: AsyncSession = Depends(get_session),
) -> list[CaseScore]:
    run = await session.get(EvalRun, run_id)
    if run is None or run.tenant_id != tenant_id:
        raise AppError("run_not_found", "run not found", 404)
    rows = (
        await session.scalars(
            select(EvalResult).where(EvalResult.run_id == run_id).order_by(EvalResult.case_key)
        )
    ).all()
    return [
        CaseScore(
            case_key=row.case_key,
            passed=row.passed,
            scores=row.scores,
            rationale=str(row.output.get("_rationale", "")),
        )
        for row in rows
    ]
