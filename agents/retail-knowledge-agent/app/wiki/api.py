# 中文说明：Wiki API：页面、版本、审核和搜索。
"""HTTP API for the Retail Knowledge Wiki.

The wiki is the source of truth; chat retrieval only consumes approved content.
A separate front-end can be built against these endpoints.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from agent_common.context import Principal
from agent_common.security import get_principal
from app.db import get_session
from app.wiki.schemas import PageCreate, PageOut, PageUpdate, ReviewRequest, RevisionOut, WikiSearchHit
from app.wiki.service import WikiService

router = APIRouter(prefix="/v1/wiki", tags=["wiki"])

ROLE_EDITOR = "knowledge-editor"
ROLE_REVIEWER = "knowledge-reviewer"


def _require(principal: Principal, *roles: str) -> None:
    if principal.is_admin:
        return
    if not principal.roles.intersection(roles):
        from agent_common.errors import AppError
        raise AppError("forbidden", "insufficient wiki role", 403)


def _service(session: AsyncSession) -> WikiService:
    return WikiService(session)


@router.get("/pages", response_model=list[PageOut])
async def list_pages(
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PageOut]:
    return [PageOut.model_validate(item) for item in await _service(session).list_pages(principal)]


@router.post("/pages", response_model=PageOut, status_code=201)
async def create_page(
    payload: PageCreate,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PageOut:
    _require(principal, ROLE_EDITOR)
    return PageOut.model_validate(await _service(session).create_page(principal, payload))


@router.get("/pages/{slug}", response_model=PageOut)
async def get_page(
    slug: str,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PageOut:
    return PageOut.model_validate(await _service(session).get_page(principal, slug))


@router.put("/pages/{slug}", response_model=PageOut)
async def update_page(
    slug: str,
    payload: PageUpdate,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PageOut:
    _require(principal, ROLE_EDITOR)
    return PageOut.model_validate(await _service(session).update_page(principal, slug, payload))


@router.post("/pages/{slug}/submit", response_model=PageOut)
async def submit_page(
    slug: str,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PageOut:
    _require(principal, ROLE_EDITOR)
    return PageOut.model_validate(await _service(session).submit(principal, slug))


@router.post("/pages/{slug}/approve", response_model=PageOut)
async def approve_page(
    slug: str,
    payload: ReviewRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PageOut:
    _require(principal, ROLE_REVIEWER)
    return PageOut.model_validate(await _service(session).approve(principal, slug, payload))


@router.post("/pages/{slug}/reject", response_model=PageOut)
async def reject_page(
    slug: str,
    payload: ReviewRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PageOut:
    _require(principal, ROLE_REVIEWER)
    return PageOut.model_validate(await _service(session).reject(principal, slug, payload))


@router.get("/pages/{slug}/revisions", response_model=list[RevisionOut])
async def revisions(
    slug: str,
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[RevisionOut]:
    return [RevisionOut.model_validate(item) for item in await _service(session).history(principal, slug)]


@router.get("/search", response_model=list[WikiSearchHit])
async def search(
    q: str = Query(min_length=1, max_length=128),
    principal: Principal = Depends(get_principal),
    session: AsyncSession = Depends(get_session),
) -> list[WikiSearchHit]:
    return [WikiSearchHit.model_validate(item) for item in await _service(session).search(principal, q)]