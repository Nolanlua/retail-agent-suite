# 中文说明：零售 Agent 的数据中台客户端：读取补货特征。
"""Data platform client for online replenishment features."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

import httpx

from app.config import settings


class DataPlatformClient:
    def __init__(self) -> None:
        self._base = settings.data_platform_url.rstrip("/")

    async def get_replenishment_features(
        self,
        *,
        tenant_id: str,
        store_id: str,
        sku: str,
        business_date: date,
    ) -> dict[str, Any] | None:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.post(
                    f"{self._base}/v1/features/query",
                    headers={
                        "X-Tenant-Id": tenant_id,
                        "X-Internal-Token": settings.internal_service_token,
                    },
                    json={
                        "feature_view": "feature_replenishment_input",
                        "store_id": store_id,
                        "sku": sku,
                        "business_date": datetime.combine(business_date, time.min).replace(tzinfo=timezone.utc).isoformat(),
                    },
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                return response.json().get("payload", {})
        except httpx.HTTPError:
            return None
