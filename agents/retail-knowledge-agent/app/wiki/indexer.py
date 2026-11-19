# 中文说明：审核通过后把 Wiki 页面写入检索索引。
"""Wiki-to-retrieval indexer.

Approval and indexing are separate steps on purpose. If the search cluster is
down, the page stays approved but index_status=failed; an operator can rebuild
the index later without losing the reviewed content.
"""
from __future__ import annotations

import structlog

from app.retrieval.retriever import KnowledgeRetriever
from app.wiki.models import WikiPage, WikiRevision

logger = structlog.get_logger(__name__)


class WikiIndexer:
    def __init__(self, retriever: KnowledgeRetriever | None = None) -> None:
        self._retriever = retriever or KnowledgeRetriever()

    async def index(self, page: WikiPage, revision: WikiRevision) -> bool:
        try:
            await self._retriever.index_page(
                chunk_id=f"wiki:{page.tenant_id}:{page.slug}:v{revision.version}",
                doc_id=str(page.id),
                title=revision.title,
                text=revision.content_md,
                source=page.source or "零售智库 Wiki",
                section=page.category,
                tenant_id=page.tenant_id,
            )
            return True
        except Exception:  # noqa: BLE001 - approval must not be lost on index outage
            logger.exception("wiki_index_failed", slug=page.slug, version=revision.version)
            return False
