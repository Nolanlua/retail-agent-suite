# 中文说明：Wiki 业务：创建、修订、送审、审核、驳回和页面查询。
"""Wiki application service.

Domain rules:
- every edit creates an immutable revision;
- a page is visible to the agent only when an approved revision exists;
- approving a revision updates the page pointer and triggers indexing;
- rejected revisions are kept for audit, never overwritten.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_common.context import Principal
from agent_common.errors import AppError
from app.wiki.indexer import WikiIndexer
from app.wiki.models import WikiPage, WikiRevision
from app.wiki.schemas import PageCreate, PageUpdate, ReviewRequest


class WikiService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._indexer = WikiIndexer()

    async def create_page(self, principal: Principal, payload: PageCreate) -> PageOutDict:
        existing = await self._session.scalar(
            select(WikiPage).where(WikiPage.tenant_id == principal.tenant_id, WikiPage.slug == payload.slug)
        )
        if existing:
            raise AppError("wiki_slug_exists", "slug already exists", 409)
        page = WikiPage(
            tenant_id=principal.tenant_id,
            slug=payload.slug,
            title=payload.title,
            category=payload.category,
            source=payload.source,
            status="draft",
            current_version=1,
            index_status="pending",
            created_by=principal.subject,
            updated_at=datetime.now(timezone.utc),
        )
        self._session.add(page)
        await self._session.flush()
        revision = WikiRevision(
            page_id=page.id,
            version=1,
            title=payload.title,
            content_md=payload.content_md,
            status="draft",
            created_by=principal.subject,
        )
        self._session.add(revision)
        await self._session.commit()
        return await self.get_page(principal, payload.slug)

    async def update_page(self, principal: Principal, slug: str, payload: PageUpdate) -> PageOutDict:
        page = await self._require_page(principal, slug)
        next_version = page.current_version + 1
        page.title = payload.title
        page.source = payload.source or page.source
        page.status = "draft"
        page.current_version = next_version
        page.index_status = "pending"
        page.updated_at = datetime.now(timezone.utc)
        revision = WikiRevision(
            page_id=page.id,
            version=next_version,
            title=payload.title,
            content_md=payload.content_md,
            status="draft",
            created_by=principal.subject,
        )
        self._session.add(revision)
        await self._session.commit()
        return await self.get_page(principal, slug)

    async def submit(self, principal: Principal, slug: str) -> PageOutDict:
        page = await self._require_page(principal, slug)
        revision = await self._latest_revision(page)
        if revision.status not in {"draft", "rejected"}:
            raise AppError("wiki_invalid_state", "only draft or rejected revisions can be submitted", 409)
        revision.status = "pending"
        page.status = "pending"
        await self._session.commit()
        return await self.get_page(principal, slug)

    async def approve(self, principal: Principal, slug: str, payload: ReviewRequest) -> PageOutDict:
        page = await self._require_page(principal, slug)
        revision = await self._latest_revision(page)
        if revision.status != "pending":
            raise AppError("wiki_invalid_state", "only pending revisions can be approved", 409)
        revision.status = "approved"
        revision.reviewer = principal.subject
        revision.review_note = payload.review_note
        page.status = "approved"
        page.updated_at = datetime.now(timezone.utc)
        await self._session.commit()
        ok = await self._indexer.index(page, revision)
        page.index_status = "indexed" if ok else "failed"
        await self._session.commit()
        return await self.get_page(principal, slug)

    async def reject(self, principal: Principal, slug: str, payload: ReviewRequest) -> PageOutDict:
        page = await self._require_page(principal, slug)
        revision = await self._latest_revision(page)
        if revision.status != "pending":
            raise AppError("wiki_invalid_state", "only pending revisions can be rejected", 409)
        revision.status = "rejected"
        revision.reviewer = principal.subject
        revision.review_note = payload.review_note
        page.status = "rejected"
        await self._session.commit()
        return await self.get_page(principal, slug)

    async def get_page(self, principal: Principal, slug: str) -> PageOutDict:
        page = await self._require_page(principal, slug)
        revision = await self._latest_revision(page)
        return {
            "slug": page.slug,
            "title": page.title,
            "category": page.category,
            "source": page.source,
            "status": page.status,
            "current_version": page.current_version,
            "index_status": page.index_status,
            "content_md": revision.content_md if revision else "",
            "updated_at": page.updated_at,
        }

    async def list_pages(self, principal: Principal, limit: int = 50) -> list[dict[str, Any]]:
        rows = (
            await self._session.scalars(
                select(WikiPage)
                .where(WikiPage.tenant_id == principal.tenant_id)
                .order_by(desc(WikiPage.updated_at))
                .limit(limit)
            )
        ).all()
        return [
            {
                "slug": row.slug,
                "title": row.title,
                "category": row.category,
                "source": row.source,
                "status": row.status,
                "current_version": row.current_version,
                "index_status": row.index_status,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]

    async def history(self, principal: Principal, slug: str) -> list[dict[str, Any]]:
        page = await self._require_page(principal, slug)
        rows = (
            await self._session.scalars(
                select(WikiRevision)
                .where(WikiRevision.page_id == page.id)
                .order_by(desc(WikiRevision.version))
            )
        ).all()
        return [
            {
                "version": row.version,
                "title": row.title,
                "content_md": row.content_md,
                "status": row.status,
                "reviewer": row.reviewer,
                "review_note": row.review_note,
                "created_by": row.created_by,
                "created_at": row.created_at,
            }
            for row in rows
        ]


    async def list_notices(self, principal: Principal, limit: int = 20) -> list[dict[str, Any]]:
        rows = (
            await self._session.scalars(
                select(WikiPage)
                .where(
                    WikiPage.tenant_id == principal.tenant_id,
                    WikiPage.status == "approved",
                    WikiPage.category == "notice",
                )
                .order_by(desc(WikiPage.updated_at))
                .limit(limit)
            )
        ).all()
        notices = []
        for row in rows:
            revision = await self._latest_revision(row)
            notices.append(
                {
                    "slug": row.slug,
                    "title": row.title,
                    "source": row.source,
                    "content_md": revision.content_md,
                    "updated_at": row.updated_at,
                }
            )
        return notices

    async def search(self, principal: Principal, query: str, limit: int = 10) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        rows = (
            await self._session.scalars(
                select(WikiPage)
                .where(
                    WikiPage.tenant_id == principal.tenant_id,
                    WikiPage.status == "approved",
                    or_(WikiPage.title.ilike(pattern), WikiPage.slug.ilike(pattern)),
                )
                .limit(limit)
            )
        ).all()
        return [
            {"slug": row.slug, "title": row.title, "source": row.source, "snippet": row.title}
            for row in rows
        ]

    async def _require_page(self, principal: Principal, slug: str) -> WikiPage:
        page = await self._session.scalar(
            select(WikiPage).where(WikiPage.tenant_id == principal.tenant_id, WikiPage.slug == slug)
        )
        if page is None:
            raise AppError("wiki_page_not_found", "wiki page not found", 404)
        return page

    async def _latest_revision(self, page: WikiPage) -> WikiRevision:
        revision = await self._session.scalar(
            select(WikiRevision)
            .where(WikiRevision.page_id == page.id)
            .order_by(desc(WikiRevision.version))
            .limit(1)
        )
        if revision is None:
            raise AppError("wiki_revision_not_found", "wiki revision not found", 404)
        return revision


PageOutDict = dict[str, Any]