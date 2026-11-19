# 中文说明：零售 Agent 的 Go 订单服务客户端。
"""Go order service adapter.

The retail agent never writes order tables directly. It calls the order service,
which owns transactions, supplier integration and idempotency.
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class OrderServiceClient:
    def __init__(self) -> None:
        self._base = settings.order_service_url.rstrip("/")

    async def get_offers(self, tenant_id: str, store_id: str, sku: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.get(
                    f"{self._base}/internal/suppliers/offers",
                    params={"store_id": store_id, "sku": sku},
                    headers={"X-Tenant-Id": tenant_id, "X-Internal-Token": settings.order_service_token},
                )
                response.raise_for_status()
                return response.json().get("offers", [])
        except httpx.HTTPError:
            return []

    async def create_order(self, tenant_id: str, payload: dict[str, Any], idempotency_key: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{self._base}/internal/orders",
                headers={
                    "X-Tenant-Id": tenant_id,
                    "X-Internal-Token": settings.order_service_token,
                    "Idempotency-Key": idempotency_key,
                },
                json=payload,
            )
            response.raise_for_status()
            return response.json()
