"""Request-scoped context.

FastAPI dependencies and background jobs both need the same tenant, request id
and principal. Context variables keep that data available without threading it
through every function signature.
"""
from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
tenant_id_ctx: ContextVar[str] = ContextVar("tenant_id", default="")
principal_ctx: ContextVar["Principal | None"] = ContextVar("principal", default=None)


@dataclass(frozen=True)
class Principal:
    subject: str
    tenant_id: str
    roles: frozenset[str]
    store_ids: frozenset[str] = frozenset()

    @property
    def is_admin(self) -> bool:
        return "platform-admin" in self.roles

    def can_access_store(self, store_id: str) -> bool:
        return self.is_admin or store_id in self.store_ids
