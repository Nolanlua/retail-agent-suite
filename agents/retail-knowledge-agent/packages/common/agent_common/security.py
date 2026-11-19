"""JWT authentication and role checks.

The service trusts a token issued by the platform identity provider. It does not
trust user ids or tenant ids supplied in headers, with one exception: the
gateway may overwrite X-Tenant-Id only after validating the token, and the
service compares both values.
"""
from __future__ import annotations

from typing import Annotated, Iterable

import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from agent_common.config import Settings, get_settings
from agent_common.context import Principal, tenant_id_ctx

bearer = HTTPBearer(auto_error=False)


def decode_token(token: str, settings: Settings) -> Principal:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or expired token",
        ) from exc

    tenant_id = str(payload.get("tenant_id", ""))
    subject = str(payload.get("sub", ""))
    if not tenant_id or not subject:
        raise HTTPException(status_code=401, detail="token missing subject or tenant")

    roles = frozenset(str(role) for role in payload.get("roles", []))
    stores = frozenset(str(store) for store in payload.get("store_ids", []))
    return Principal(subject=subject, tenant_id=tenant_id, roles=roles, store_ids=stores)


async def get_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
    tenant_header: Annotated[str | None, Header(alias="X-Tenant-Id")] = None,
) -> Principal:
    if credentials is None:
        raise HTTPException(status_code=401, detail="missing bearer token")

    principal = decode_token(credentials.credentials, settings)
    if tenant_header and tenant_header != principal.tenant_id:
        # A mismatch means the gateway and token disagree. Fail closed.
        raise HTTPException(status_code=403, detail="tenant header does not match token")
    tenant_id_ctx.set(principal.tenant_id)
    return principal


def require_roles(*allowed: str):
    """Dependency factory for coarse-grained RBAC.

    Domain-level checks (for example store ownership) still belong in the
    service layer; roles are only the first gate.
    """
    allowed_set = frozenset(allowed)

    async def dependency(principal: Annotated[Principal, Depends(get_principal)]) -> Principal:
        if not principal.roles.intersection(allowed_set) and not principal.is_admin:
            raise HTTPException(status_code=403, detail="insufficient role")
        return principal

    return dependency


def verify_internal_token(token: str | None, settings: Settings) -> None:
    if not token or token != settings.internal_service_token:
        raise HTTPException(status_code=401, detail="invalid internal service token")


def roles_have_any(roles: Iterable[str], allowed: Iterable[str]) -> bool:
    return bool(set(roles).intersection(allowed))
