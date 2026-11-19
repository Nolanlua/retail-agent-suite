"""A single error contract for every API in the suite.

Clients should not have to parse three different error formats. Every handler
returns code, message, request_id and optional details.
"""
from __future__ import annotations

from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from agent_common.context import request_id_ctx


class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id_ctx.get(),
                "details": exc.details,
            }
        },
    )


async def unhandled_error_handler(_request: Request, _exc: Exception) -> JSONResponse:
    # Do not leak stack traces or upstream payloads to callers.
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_error",
                "message": "internal server error",
                "request_id": request_id_ctx.get(),
                "details": {},
            }
        },
    )
