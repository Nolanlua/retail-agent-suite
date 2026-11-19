# 中文说明：零售智库聊天与检索 API。
"""HTTP API for the retail knowledge agent."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from agent_common.context import Principal
from agent_common.security import get_principal
from app.config import settings
from app.db import get_session
from app.wiki.models import WikiPage
from app.schemas import ChatRequest, ChatResponse, CitationOut, NoticeOut, SearchHit, SearchRequest
from app.services.chat import ChatService
from app.wiki.service import WikiService

router = APIRouter()


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "retail-knowledge-agent"}


@router.post("/v1/chat", response_model=ChatResponse)
async def chat(
    payload: ChatRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> ChatResponse:
    result = await service.ask(
        question=payload.question,
        tenant_id=principal.tenant_id,
        conversation_id=payload.conversation_id,
        history=payload.history,
    )
    return ChatResponse(
        conversation_id=payload.conversation_id or result.trace.get("thread_id", ""),
        answer=result.answer,
        citations=[CitationOut.model_validate(item) for item in result.citations],
        intent=result.intent,
        safety=result.safety,
        latency_ms=result.latency_ms,
        trace=result.trace,
    )


@router.post("/v1/knowledge/search", response_model=list[SearchHit])
async def search(
    payload: SearchRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[SearchHit]:
    chunks = await service._retriever.retrieve(payload.query, tenant_id=principal.tenant_id, top_k=payload.top_k)
    return [
        SearchHit(
            chunk_id=item.chunk_id,
            doc_id=item.doc_id,
            title=item.title,
            source=item.source,
            text=item.text,
            score=item.score,
        )
        for item in chunks
    ]

@router.get("/v1/notices", response_model=list[NoticeOut])
async def notices(
    principal: Annotated[Principal, Depends(get_principal)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[NoticeOut]:
    rows = await WikiService(session).list_notices(principal)
    return [NoticeOut.model_validate(item) for item in rows]

@router.get("/internal/notices", response_model=list[NoticeOut])
async def internal_notices(
    tenant_id: str = Header(alias="X-Tenant-Id"),
    x_internal_token: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[NoticeOut]:
    if x_internal_token != settings.internal_service_token:
        raise HTTPException(status_code=401, detail="invalid internal token")
    # 内部服务使用受限 Principal，只读取本租户 approved 公告。
    principal = Principal(subject="retail-ordering-agent", tenant_id=tenant_id, roles=frozenset({"service"}))
    rows = await WikiService(session).list_notices(principal)
    return [NoticeOut.model_validate(item) for item in rows]
