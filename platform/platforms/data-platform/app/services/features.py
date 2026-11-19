# 中文说明：在线特征服务：按业务日期取最近快照，并检查数据新鲜度。
"""Online feature serving.

Features are point-in-time snapshots. The agent never queries raw sales tables;
it asks for a named feature view, which makes offline/online consistency and
lineage auditable.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FeatureSnapshot
from app.schemas import FeaturePoint, FeatureSnapshotWrite


async def get_feature_point(
    session: AsyncSession,
    *,
    feature_view: str,
    store_id: str,
    sku: str,
    business_date: datetime,
    max_staleness_hours: int,
) -> FeaturePoint | None:
    entity_key = f"{store_id}:{sku}"
    stmt = (
        select(FeatureSnapshot)
        .where(
            FeatureSnapshot.feature_view == feature_view,
            FeatureSnapshot.entity_key == entity_key,
            FeatureSnapshot.business_date <= business_date,
        )
        .order_by(desc(FeatureSnapshot.business_date))
        .limit(1)
    )
    row = await session.scalar(stmt)
    if row is None:
        return None

    created = row.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - created > timedelta(hours=max_staleness_hours):
        return None

    return FeaturePoint(
        entity_key=row.entity_key,
        business_date=row.business_date,
        version=row.version,
        payload=row.payload,
    )


async def upsert_feature_point(
    session: AsyncSession,
    *,
    tenant_id: str,
    payload: FeatureSnapshotWrite,
) -> None:
    stmt = (
        insert(FeatureSnapshot)
        .values(
            tenant_id=tenant_id,
            feature_view=payload.feature_view,
            entity_key=payload.entity_key,
            business_date=payload.business_date,
            payload=payload.payload,
            version=payload.version,
        )
        .on_conflict_do_update(
            constraint="uq_feature_point",
            set_={"payload": payload.payload, "version": payload.version},
        )
    )
    await session.execute(stmt)
    await session.commit()
