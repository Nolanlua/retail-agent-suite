# 中文说明：零售订货 Agent FastAPI 入口。
"""Retail ordering agent FastAPI entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from agent_common.errors import AppError, app_error_handler, unhandled_error_handler
from agent_common.logging import configure_logging
from app.api import router
from app.config import settings
from app.services.ordering import OrderingService


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.app_env, settings.log_level)
    app.state.ordering_service = OrderingService()
    yield


app = FastAPI(
    title="零售智能订货 Agent",
    version="1.0.0",
    description="Forecast, replenishment constraints, supplier matching and human-confirmed ordering.",
    lifespan=lifespan,
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)


@app.exception_handler(PermissionError)
async def permission_error_handler(_request: Request, exc: PermissionError) -> JSONResponse:
    return JSONResponse(status_code=403, content={"error": {"code": "forbidden", "message": str(exc)}})


app.include_router(router)
app.mount("/metrics", make_asgi_app())
