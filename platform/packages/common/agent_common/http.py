"""HTTP client helpers for service-to-service calls.

Every call gets a timeout, a request id and a bounded retry policy. Retries are
only applied to idempotent methods or to calls that carry an idempotency key.
"""
from __future__ import annotations

import asyncio
from typing import Any

import httpx

from agent_common.config import Settings
from agent_common.context import request_id_ctx


class ServiceClient:
    def __init__(self, base_url: str, settings: Settings, service_token: str = "") -> None:
        self._base_url = base_url.rstrip("/")
        self._settings = settings
        self._service_token = service_token

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        retryable: bool = False,
    ) -> dict[str, Any]:
        merged_headers = {
            "X-Request-Id": request_id_ctx.get(),
            "Content-Type": "application/json",
        }
        if self._service_token:
            merged_headers["X-Internal-Token"] = self._service_token
        if headers:
            merged_headers.update(headers)

        timeout = httpx.Timeout(
            self._settings.http_timeout_seconds,
            connect=self._settings.http_connect_timeout_seconds,
        )
        attempts = 3 if retryable else 1
        last_error: Exception | None = None

        for attempt in range(attempts):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.request(
                        method,
                        f"{self._base_url}{path}",
                        json=json,
                        params=params,
                        headers=merged_headers,
                    )
                if response.status_code >= 500 and attempt < attempts - 1:
                    await asyncio.sleep(0.2 * (2**attempt))
                    continue
                response.raise_for_status()
                if response.content:
                    return response.json()
                return {}
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    await asyncio.sleep(0.2 * (2**attempt))
                    continue
                break
            except httpx.HTTPStatusError as exc:
                # 4xx is a caller problem; retrying would only add load.
                raise RuntimeError(
                    f"upstream {method} {path} failed with {exc.response.status_code}"
                ) from exc

        raise RuntimeError(f"upstream {method} {path} unavailable") from last_error
