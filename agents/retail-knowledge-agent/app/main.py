# 中文说明：零售智库入口：初始化数据库、Wiki 路由和聊天 Agent。
"""retail knowledge agent FastAPI entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from prometheus_client import make_asgi_app

from agent_common.errors import AppError, app_error_handler, unhandled_error_handler
from agent_common.logging import configure_logging
from app.api import router
from app.config import settings
from app.db import Base, engine
from app.services.chat import ChatService
from app.wiki.api import router as wiki_router
from app.wiki import models as wiki_models  # noqa: F401 - register metadata


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.service_name, settings.app_env, settings.log_level)
    if settings.app_env == "local":
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    app.state.chat_service = ChatService()
    yield
    await engine.dispose()


app = FastAPI(
    title="零售智库 · Retail Knowledge Agent",
    version="1.0.0",
    description="Enterprise retail knowledge agent with hybrid retrieval, graph expansion, citations and safety guardrails.",
    lifespan=lifespan,
)
app.add_exception_handler(AppError, app_error_handler)
app.add_exception_handler(Exception, unhandled_error_handler)
app.include_router(router)
app.include_router(wiki_router)
app.mount("/metrics", make_asgi_app())