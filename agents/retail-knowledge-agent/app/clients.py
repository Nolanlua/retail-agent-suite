"""Outbound clients used by the retail knowledge agent.

All clients are thin adapters. They never contain medical logic; they only move
data between the agent and platform services.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx

from app.config import settings


class LLMClient:
    def __init__(self) -> None:
        self._base = settings.llm_base_url.rstrip("/")

    async def chat(self, system: str, user: str, *, temperature: float = 0.1) -> str:
        if not settings.llm_api_key:
            raise RuntimeError("LLM_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.post(
                f"{self._base}/chat/completions",
                headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                json={
                    "model": settings.llm_model,
                    "temperature": temperature,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
            )
            response.raise_for_status()
            return str(response.json()["choices"][0]["message"]["content"]).strip()


class DataPlatformClient:
    """Read-only client for catalog and lineage metadata."""

    def __init__(self) -> None:
        self._base = settings.data_platform_url.rstrip("/")

    async def get_asset(self, asset_id: str, tenant_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(
                f"{self._base}/v1/assets",
                headers={"X-Tenant-Id": tenant_id},
            )
            response.raise_for_status()
            return {"assets": response.json(), "asset_id": asset_id}


class EvalPlatformClient:
    """Online feedback bridge.

    Offline evaluation is driven by the evaluation platform. This client only
    records a small sample of production traces for later human review.
    """

    def __init__(self) -> None:
        self._base = settings.eval_platform_url.rstrip("/")

    async def record_trace(self, tenant_id: str, payload: dict[str, Any]) -> None:
        # Fire-and-forget by design; evaluation must not slow down chat.
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                await client.post(
                    f"{self._base}/v1/online-traces",
                    headers={"X-Tenant-Id": tenant_id, "X-Internal-Token": settings.internal_service_token},
                    json=payload,
                )
        except Exception:  # noqa: BLE001 - telemetry is best effort
            return
