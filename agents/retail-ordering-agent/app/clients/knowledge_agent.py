"""零售智库公告客户端。

订货 Agent 不复制公告内容，而是从知识库读取已审核的 notice 页面。
这样召回、陈列变更、价格调整只有一个事实源。
"""
from __future__ import annotations

from typing import Any

import httpx

from app.config import settings


class KnowledgeAgentClient:
    def __init__(self) -> None:
        self._base = settings.knowledge_agent_url.rstrip("/")

    async def get_notices(self, tenant_id: str) -> list[dict[str, Any]]:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self._base}/internal/notices",
                    headers={"X-Tenant-Id": tenant_id, "X-Internal-Token": settings.internal_service_token},
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError:
            # 公告不可用不能阻塞补货计算；结果中标记 notice_unavailable。
            return []