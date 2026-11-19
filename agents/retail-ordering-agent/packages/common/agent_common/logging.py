"""Structured logging with request and tenant fields.

Plain text logs are hard to query across services. Every line is JSON and
includes service, environment, request id and tenant id, which makes Loki or
ELK queries predictable during an incident.
"""
from __future__ import annotations

import logging
import sys

import structlog

from agent_common.context import request_id_ctx, tenant_id_ctx


def configure_logging(service_name: str, environment: str, level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(message)s",
        stream=sys.stdout,
    )

    def add_context(_logger, _method, event_dict):
        event_dict.setdefault("service", service_name)
        event_dict.setdefault("env", environment)
        event_dict.setdefault("request_id", request_id_ctx.get())
        event_dict.setdefault("tenant_id", tenant_id_ctx.get())
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            add_context,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.JSONRenderer(ensure_ascii=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
