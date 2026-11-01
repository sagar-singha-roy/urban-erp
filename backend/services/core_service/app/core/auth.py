import logging
from typing import Dict, List, Optional, Set
from fastapi import Depends, HTTPException, Request, Security, status, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import httpx
from jose import jwt, JWTError
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.tenant_context import SET_RLS_CONTEXT_SQL, rls_params, set_rls_context
from app.db.models import GlobalUserProfile, RoleModel, RolePermission, StateTenant, Tenant, User
from app.db.session import AsyncReadSessionLocal, get_read_db

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)

_jwks_cache: Optional[Dict] = None
SUPER_ADMIN = "super_admin"
BLOCKED_ACCOUNT_STATUSES = ("Suspended", "Deactivated")
# Token roles mapped to the permission matrix's role codes.
ROLE_CODES = {
    "state_director": "STATE_DIRECTOR",
    "revenue_officer": "TAX_INSPECTOR",
    "town_planner": "TOWN_PLANNER",
    "citizen": "CITIZEN_READONLY",
}
PERMISSION_COLUMNS = {
    "VIEW": "can_view",
    "CREATE": "can_create",
    "UPDATE": "can_update",
    "DELETE": "can_delete",
    "APPROVE": "can_approve",
    "EXPORT": "can_export",
    "MANAGE": "can_manage",
}

async def get_keycloak_jwks() -> Dict:
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    jwks_url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/certs"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(jwks_url)
            if resp.status_code == 200:
                _jwks_cache = resp.json()
                return _jwks_cache
    except Exception as e:
        logger.warning(f"Failed to fetch Keycloak JWKS from {jwks_url}: {e}")
    return {}

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security)
) -> Dict:
    user = await _authenticate(credentials)
    set_rls_context(user_tenant_scope(user), bypass=is_super_admin(user))
    return user


def keycloak_token_is_for_this_client(payload: Dict) -> bool:
    """Keycloak puts the client in azp and often only "account" in aud, so accept either."""
    client = settings.KEYCLOAK_CLIENT_ID
    audience = payload.get("aud") or []
    audiences = [audience] if isinstance(audience, str) else audience
    return client in audiences or payload.get("azp") == client


async def _apply_current_account_state(payload: Dict) -> Dict:
    """Tokens outlive account changes, so status and role always come from the database."""
    async with AsyncReadSessionLocal() as db:
        user = await db.scalar(select(User).where(User.id == str(payload.get("sub") or "")))
        profile = None
        if user:
            profile = await db.scalar(select(GlobalUserProfile).where(GlobalUserProfile.email == user.email))
    if not user or not user.is_active or (profile and profile.account_status in BLOCKED_ACCOUNT_STATUSES):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This account is no longer active",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {**payload, "realm_access": {"roles": [user.role]}}


async def _authenticate(credentials: Optional[HTTPAuthorizationCredentials]) -> Dict:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    # 1. First check if token is signed with our internal SSO secret
    from app.core.security import decode_access_token
    internal_payload = decode_access_token(token)
    if internal_payload:
        return await _apply_current_account_state(internal_payload)

    # 2. Check Keycloak JWKS
    jwks = await get_keycloak_jwks()

    try:
        unverified_header = jwt.get_unverified_header(token)
        rsa_key = {}
        for key in jwks.get("keys", []):
            if key["kid"] == unverified_header.get("kid"):
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key.get("use"),
                    "n": key["n"],
                    "e": key["e"]
                }
                break

        if rsa_key:
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=["RS256"],
                options={"verify_aud": False}
            )
            if not keycloak_token_is_for_this_client(payload):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token was not issued for this application",
                )
            return payload
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unable to find appropriate signing key"
            )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}"
        )

def require_roles(allowed_roles: List[str]):
    async def role_checker(user: Dict = Depends(get_current_user)) -> Dict:
        user_roles = user.get("realm_access", {}).get("roles", [])
        if any(role in user_roles for role in allowed_roles) or "super_admin" in user_roles:
            return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Operation requires one of the following roles: {allowed_roles}"
        )
    return role_checker

def is_super_admin(user: Dict) -> bool:
    return SUPER_ADMIN in user.get("realm_access", {}).get("roles", [])


def require_permission(component_code: str, action: str):
    """Enforces a component action from the role permission matrix, e.g. PTX-P10:APPROVE."""
    column = getattr(RolePermission, PERMISSION_COLUMNS[action])

    async def permission_checker(
        user: Dict = Depends(get_current_user),
        db: AsyncSession = Depends(get_read_db),
    ) -> Dict:
        if is_super_admin(user):
            return user
        codes = [ROLE_CODES[r] for r in user.get("realm_access", {}).get("roles", []) if r in ROLE_CODES]
        allowed = bool(codes) and await db.scalar(
            select(RolePermission.id)
            .join(RoleModel, RolePermission.role_id == RoleModel.id)
            .where(RoleModel.code.in_(codes), RolePermission.component_code == component_code, column.is_(True))
            .limit(1)
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires {component_code}:{action}",
            )
        return user

    return permission_checker


def require_state_scope_for_reads():
    """Lets state directors in for their own state. Unscoped requests stay with super admins."""

    async def checker(
        request: Request,
        user: Dict = Depends(require_roles(["state_director"])),
        db: AsyncSession = Depends(get_read_db),
    ) -> None:
        if is_super_admin(user):
            return
        scoped = [
            request.path_params.get("state_tenant_id"),
            request.path_params.get("ulb_tenant_id"),
            request.query_params.get("state_tenant_id"),
        ]
        scoped = [value for value in scoped if value]
        for tenant_id in scoped:
            await ensure_tenant_access(tenant_id, user, db)
        if request.method == "GET" and not scoped:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Choose a state within your scope")

    return checker


async def require_staff(user: Dict = Depends(get_current_user)) -> Dict:
    """Allow municipal staff only. Citizens have no ownership checks on bulk data yet."""
    roles = user.get("realm_access", {}).get("roles", [])
    if roles and any(role != "citizen" for role in roles):
        return user
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operation requires a staff role")


def user_tenant_scope(user: Dict) -> Set[str]:
    """Tenant identifiers granted to the user by their signed token."""
    raw = user.get("tenant_scope") or user.get("tenant_id") or ""
    return {part.strip().upper() for part in str(raw).split(",") if part.strip()}


def tenant_scope_filter(user: Dict):
    """SQLAlchemy condition limiting Tenant rows to the user's scope."""
    scope = user_tenant_scope(user)
    return or_(
        func.upper(Tenant.tenant_id).in_(scope),
        func.upper(Tenant.parent_state_tenant_id).in_(scope),
        func.upper(Tenant.state_code).in_(scope),
    )


async def _tenant_identifiers(tenant_id: str, db: AsyncSession) -> Set[str]:
    """The tenant's own identifiers plus those of the state that contains it."""
    identifiers = {tenant_id}
    tenant = await db.scalar(select(Tenant).where(func.upper(Tenant.tenant_id) == tenant_id))
    if tenant:
        identifiers.update(v.upper() for v in (tenant.parent_state_tenant_id, tenant.state_code) if v)
    state = await db.scalar(
        select(StateTenant).where(
            or_(func.upper(StateTenant.tenant_id) == tenant_id, func.upper(StateTenant.state_code) == tenant_id)
        )
    )
    if state:
        identifiers.update(v.upper() for v in (state.tenant_id, state.state_code) if v)
    return identifiers


async def can_access_tenant(tenant_id: str, user: Dict, db: AsyncSession) -> bool:
    if is_super_admin(user):
        return True
    normalized = tenant_id.strip().upper()
    scope = user_tenant_scope(user)
    if normalized in scope:
        return True
    return bool(scope & await _tenant_identifiers(normalized, db))


async def ensure_tenant_access(tenant_id: str, user: Dict, db: AsyncSession) -> None:
    if not await can_access_tenant(tenant_id, user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to this tenant")


async def require_path_tenant_access(
    request: Request,
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
) -> None:
    """Router dependency that authorizes a {tenant_id} path parameter when one is present."""
    tenant_id = request.path_params.get("tenant_id")
    if tenant_id:
        await ensure_tenant_access(tenant_id, user, db)


def _concrete_sub_tenant(x_sub_tenant_id: Optional[str]) -> Optional[str]:
    cleaned = (x_sub_tenant_id or "").strip().upper()
    return cleaned if cleaned and cleaned != "ALL" else None


async def get_current_sub_tenant(
    x_sub_tenant_id: Optional[str] = Header(None, alias="X-Sub-Tenant-ID"),
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
) -> Optional[str]:
    """Return the authorized city context, or None for statewide context."""
    sub_tenant = _concrete_sub_tenant(x_sub_tenant_id)
    if sub_tenant:
        await ensure_tenant_access(sub_tenant, user, db)
    return sub_tenant


async def _narrow_rls_scope(tenant_id: str, db: Optional[AsyncSession]) -> str:
    """Limit the database to the resolved tenant, including the transaction already open."""
    set_rls_context([tenant_id])
    if db is not None:
        await db.execute(text(SET_RLS_CONTEXT_SQL), rls_params())
    return tenant_id


async def get_current_tenant(
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-ID"),
    sub_tenant: Optional[str] = Depends(get_current_sub_tenant),
    user: Dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
) -> str:
    """
    Resolve the tenant whose municipal rows this request may touch.
    Precedence: authorized X-Sub-Tenant-ID, then authorized X-Tenant-ID, then the token's own tenant.
    Municipal rows are stored against the city, so a city context takes priority over its state.
    """
    if sub_tenant:
        return await _narrow_rls_scope(sub_tenant, db)
    requested = (x_tenant_id or "").strip().upper()
    if requested:
        await ensure_tenant_access(requested, user, db)
        return await _narrow_rls_scope(requested, db)
    token_tenants = str(user.get("tenant_id") or "").split(",")
    resolved = token_tenants[0].strip().upper()
    if resolved:
        return await _narrow_rls_scope(resolved, db)
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No tenant context is available for this user")
