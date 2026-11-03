"""ADM-R02 change history. Each change is kept in the history table and as a hash-chained audit vault event."""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.audit_vault import record_immutable_audit_event
from app.core.cross_tenant_rules import describe_scope
from app.db.models import AccessChangeHistory, CrossTenantAccessGrant

AUDIT_CATEGORY = "Authorisation"
HIGH_SEVERITY_ACTIONS = ("REVOKED", "REVIEW_REVOKED", "EXPIRED")


def client_ip(request) -> Optional[str]:
    """The gateway overwrites X-Forwarded-For with the caller's address, and uvicorn applies it to request.client."""
    return request.client.host if request is not None and request.client else None


async def record_change(
    db: AsyncSession,
    grant: CrossTenantAccessGrant,
    action: str,
    changed_by: str,
    ip_address: Optional[str],
    reason: Optional[str] = None,
    previous_level: Optional[str] = None,
    previous_scope: Optional[str] = None,
) -> None:
    targets = [t.target_tenant_id for t in grant.targets]
    new_scope = describe_scope(grant.scope)
    db.add(AccessChangeHistory(
        grant_id=grant.id, user_email=grant.user_email, home_tenant_id=grant.home_tenant_id, target_tenant_ids=targets,
        previous_access_level=previous_level, new_access_level=grant.access_level, previous_scope=previous_scope, new_scope=new_scope,
        action=action, changed_by=changed_by, ip_address=ip_address, reason=reason, approval_reference=grant.approval_reference,
    ))
    await record_immutable_audit_event(
        db, event_category=AUDIT_CATEGORY, action=f"CROSS_TENANT_{action}"[:100], actor_id=changed_by, actor_role="Platform Super Admin",
        tenant_id=grant.home_tenant_id, severity="High" if action in HIGH_SEVERITY_ACTIONS else "Medium", ip_address=ip_address or "unknown",
        details={"grantId": grant.id, "user": grant.user_email, "targets": targets, "status": grant.status, "accessLevel": grant.access_level,
                 "previousAccessLevel": previous_level, "scope": new_scope, "reason": reason, "approvalReference": grant.approval_reference},
    )
