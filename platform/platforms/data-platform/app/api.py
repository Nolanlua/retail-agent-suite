# 中文说明：数据中台 API：资产目录、质量任务、特征查询和血缘。
"""HTTP API for the data platform.

Endpoint groups:
- /v1/assets: catalog registration and discovery
- /v1/quality: data quality execution and reports
- /v1/features: online feature serving for agents
- /v1/lineage: upstream/downstream exploration
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_common.errors import AppError
from app.config import settings
from app.db import get_session
from app.models import DataAsset, FeatureSnapshot, LineageEdge, QualityRun
from app.schemas import (
    AssetCreate,
    AssetOut,
    FeaturePoint,
    FeatureQuery,
    FeatureSnapshotWrite,
    LineageOut,
    QualityRunOut,
    QualityRunRequest,
)
from app.services.features import get_feature_point, upsert_feature_point
from app.services.quality import run_quality

router = APIRouter()


def _check_internal(token: str | None) -> None:
    if token != settings.internal_service_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid internal token")


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "data-platform"}


@router.get("/readyz")
async def readyz(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(select(1))
    return {"status": "ready"}


@router.post("/v1/assets", response_model=AssetOut, status_code=201)
async def create_asset(
    payload: AssetCreate,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    session: AsyncSession = Depends(get_session),
) -> AssetOut:
    asset = DataAsset(
        tenant_id=tenant_id,
        name=payload.name,
        domain=payload.domain,
        asset_type=payload.asset_type,
        storage_uri=payload.storage_uri,
        owner=payload.owner,
        sensitivity=payload.sensitivity,
        description=payload.description,
    )
    session.add(asset)
    await session.commit()
    await session.refresh(asset)
    return AssetOut.model_validate(asset)


@router.get("/v1/assets", response_model=list[AssetOut])
async def list_assets(
    domain: str | None = None,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    session: AsyncSession = Depends(get_session),
) -> list[AssetOut]:
    stmt = select(DataAsset).where(DataAsset.tenant_id == tenant_id).order_by(desc(DataAsset.created_at))
    if domain:
        stmt = stmt.where(DataAsset.domain == domain)
    rows = (await session.scalars(stmt)).all()
    return [AssetOut.model_validate(row) for row in rows]


@router.post("/v1/quality/run", response_model=QualityRunOut)
async def start_quality_run(
    payload: QualityRunRequest,
    x_internal_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> QualityRunOut:
    _check_internal(x_internal_token)
    run = QualityRun(
        tenant_id="",
        asset_id=payload.asset_id,
        ruleset=payload.ruleset,
        status="running",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    try:
        report = await run_quality(payload.ruleset, payload.sample_uri)
        run.status = "passed" if report["failed_rows"] == 0 else "failed"
        run.checked_rows = report["checked_rows"]
        run.failed_rows = report["failed_rows"]
        run.report = report
    except Exception as exc:  # noqa: BLE001 - persisted for operators
        run.status = "error"
        run.report = {"error": str(exc)}
    await session.commit()
    await session.refresh(run)
    return QualityRunOut.model_validate(run)


@router.get("/v1/quality/runs/{run_id}", response_model=QualityRunOut)
async def get_quality_run(run_id: UUID, session: AsyncSession = Depends(get_session)) -> QualityRunOut:
    run = await session.get(QualityRun, run_id)
    if run is None:
        raise AppError("quality_run_not_found", "quality run not found", 404)
    return QualityRunOut.model_validate(run)


@router.post("/v1/features/query", response_model=FeaturePoint)
async def query_feature(
    payload: FeatureQuery,
    x_internal_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> FeaturePoint:
    _check_internal(x_internal_token)
    point = await get_feature_point(
        session,
        feature_view=payload.feature_view,
        store_id=payload.store_id,
        sku=payload.sku,
        business_date=payload.business_date,
        max_staleness_hours=settings.feature_max_staleness_hours,
    )
    if point is None:
        raise AppError("feature_not_found", "feature point not found or stale", 404)
    return point


@router.post("/v1/features/snapshot", status_code=204)
async def write_feature(
    payload: FeatureSnapshotWrite,
    tenant_id: str = Header(alias="X-Tenant-Id"),
    x_internal_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> None:
    _check_internal(x_internal_token)
    await upsert_feature_point(session, tenant_id=tenant_id, payload=payload)


@router.get("/v1/lineage/{asset_name}", response_model=list[LineageOut])
async def get_lineage(asset_name: str, session: AsyncSession = Depends(get_session)) -> list[LineageOut]:
    rows = (
        await session.scalars(
            select(LineageEdge).where(
                (LineageEdge.upstream == asset_name) | (LineageEdge.downstream == asset_name)
            )
        )
    ).all()
    return [LineageOut.model_validate(row) for row in rows]


@router.get("/v1/features/health")
async def feature_health(session: AsyncSession = Depends(get_session)) -> dict[str, int]:
    count = len((await session.scalars(select(FeatureSnapshot.id).limit(1))).all())
    return {"feature_views": count}