# 中文说明：评测中台 FastAPI 入口。
"""Evaluation platform FastAPI application."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from agent_common.errors import AppError, app_error_handler, unhandled_error_handler
from agent_common.logging import configure_logging
from app.api import router
from app.config import settings
from app.db import engine
from app.models import Base


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.service_name, settings.app_env, settings.log_level)
    if settings.app_env == "local":
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="Enterprise Evaluation Platform",
    version="1.0.0",
    description="Versioned golden sets, evaluation runs, judges and regression reports.",
    lifespan=lifespan,
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(router)
app.mount("/metrics", make_asgi_app())
