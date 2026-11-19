# 中文说明：零售订货 API：补货建议和人工确认下单。
"""HTTP API for the retail ordering agent."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from agent_common.context import Principal
from agent_common.security import get_principal
from app.schemas import ConfirmRequest, ConfirmResponse, NoticeOut, ReminderOut, SuggestionRequest, SuggestionResponse, SupplierOut
from app.services.ordering import OrderingService

router = APIRouter()


def get_ordering_service(request: Request) -> OrderingService:
    return request.app.state.ordering_service


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "retail-ordering-agent"}


@router.post("/v1/ordering/suggest", response_model=SuggestionResponse)
async def suggest(
    payload: SuggestionRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    service: Annotated[OrderingService, Depends(get_ordering_service)],
) -> SuggestionResponse:
    result = await service.suggest(
        question=payload.question,
        tenant_id=principal.tenant_id,
        store_id=payload.store_id,
        sku=payload.sku,
        coverage_days=payload.coverage_days,
    )
    if result.store_id and not principal.can_access_store(result.store_id):
        raise PermissionError("store access denied")
    supplier = SupplierOut.model_validate(result.supplier) if result.supplier else None
    return SuggestionResponse(
        store_id=result.store_id,
        sku=result.sku,
        target_date=result.target_date,
        suggested_qty=result.suggested_qty,
        explanation=result.explanation,
        forecast=result.forecast,
        risks=result.risks,
        reasons=result.reasons,
        supplier=supplier,
        notices=[NoticeOut.model_validate(item) for item in result.notices],
        reminders=[ReminderOut.model_validate(item) for item in result.reminders],
        trace=result.trace,
    )


@router.post("/v1/ordering/confirm", response_model=ConfirmResponse)
async def confirm(
    payload: ConfirmRequest,
    principal: Annotated[Principal, Depends(get_principal)],
    service: Annotated[OrderingService, Depends(get_ordering_service)],
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> ConfirmResponse:
    if not principal.can_access_store(payload.store_id):
        raise PermissionError("store access denied")
    key = payload.idempotency_key or idempotency_header or f"order:{principal.subject}:{uuid.uuid4().hex}"
    result = await service.confirm(
        tenant_id=principal.tenant_id,
        store_id=payload.store_id,
        sku=payload.sku,
        qty=payload.qty,
        supplier_code=payload.supplier_code,
        supplier_sku=payload.supplier_sku,
        unit_price=payload.unit_price,
        operator=principal.subject,
        idempotency_key=key,
    )
    return ConfirmResponse(
        order_id=str(result.get("order_id", "")),
        status=str(result.get("status", "unknown")),
        idempotent=bool(result.get("idempotent", False)),
    )