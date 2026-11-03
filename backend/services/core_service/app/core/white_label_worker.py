"""Background upkeep for ADM-T04: lapsed claims, re-verification, certificate status and gateway files."""
import asyncio
import datetime
import logging
from pathlib import Path
from typing import List, Optional

from sqlalchemy import or_, select
from sqlalchemy.orm import undefer

from app.core import certificates as certs
from app.core import white_label_rules as rules
from app.core.config import settings
from app.core.domain_verification import verify_domain
from app.core.gateway_sync import Site, render_files, write_candidate
from app.core.tenant_context import set_rls_context
from app.db.models import DomainMapping, TenantAuditLog, TenantCertificate, TenantDomain
from app.db.session import AsyncWriteSessionLocal

logger = logging.getLogger(__name__)

TICK_SECONDS = 60
RECHECK_AFTER = datetime.timedelta(hours=6)
USABLE_CERTIFICATE = ("Active", "Expiring Soon")


async def expire_stale_claims(db) -> None:
    now = datetime.datetime.utcnow()
    rows = (await db.scalars(select(TenantDomain).where(
        TenantDomain.verification_status.in_(["Pending", "Failed"]), TenantDomain.claim_expires_at < now,
    ))).all()
    for domain in rows:
        domain.verification_status = "Expired"
        domain.last_check_message = "The claim expired before ownership was verified."


async def recheck_verified_domains(db) -> None:
    """Ownership can lapse. A domain that no longer proves it stops routing, which also blocks subdomain takeover."""
    now = datetime.datetime.utcnow()
    rows = (await db.scalars(select(TenantDomain).where(
        TenantDomain.verification_status == "Verified",
        or_(TenantDomain.last_checked_at.is_(None), TenantDomain.last_checked_at < now - RECHECK_AFTER),
    ))).all()
    for domain in rows:
        result = await verify_domain(domain.domain_name, domain.verification_method, domain.verification_token)
        domain.last_checked_at = now
        domain.last_check_message = result.message[:255]
        if not result.verified and result.conclusive:
            domain.verification_status = "Failed"
            domain.claim_expires_at = now + datetime.timedelta(days=7)
            domain.domain_status = "Suspended"
            db.add(TenantAuditLog(tenant_id=domain.tenant_id, action="DOMAIN_VERIFICATION_LOST", performed_by="system",
                                  details=f"{domain.domain_name} suspended: {result.message}"))


def _read_issued(domain: str, name: str) -> Optional[str]:
    path = Path(settings.LETSENCRYPT_DIR) / "live" / domain / name
    return path.read_text() if path.exists() else None


async def refresh_certificates(db) -> None:
    rows = (await db.execute(
        select(TenantCertificate, TenantDomain.domain_name).join(TenantDomain, TenantCertificate.domain_id == TenantDomain.id)
    )).all()
    now = datetime.datetime.utcnow()
    for record, domain_name in rows:
        if record.provider == rules.CERTIFICATE_ACME:
            issued = _read_issued(domain_name, "fullchain.pem")
            if issued:
                record.expiry_date = certs.parse_certificate(issued).expiry
                record.status_message = None
        record.certificate_status = certs.status_for_expiry(record.expiry_date, record.renewal_notification_days)
        record.last_validation_at = now


def _tls_material(record: TenantCertificate, domain_name: str):
    if record.provider == rules.CERTIFICATE_ACME:
        return _read_issued(domain_name, "fullchain.pem"), _read_issued(domain_name, "privkey.pem")
    fullchain = (record.certificate_pem or "").rstrip("\n") + "\n" + (record.certificate_chain_pem or "")
    return fullchain, certs.decrypt_private_key(record.private_key_encrypted)


async def build_gateway_files(db) -> dict:
    now = datetime.datetime.utcnow()
    domains = (await db.scalars(select(TenantDomain).where(
        TenantDomain.verification_status == "Verified", TenantDomain.domain_status == "Active",
    ))).all()
    sites: List[Site] = []
    acme_domains: List[str] = []
    for domain in domains:
        certificates = (await db.scalars(
            select(TenantCertificate).where(TenantCertificate.domain_id == domain.id)
            .order_by(TenantCertificate.created_at.desc()).options(undefer(TenantCertificate.private_key_encrypted))
        )).all()
        mapping = await db.scalar(select(DomainMapping).where(
            DomainMapping.domain_id == domain.id, DomainMapping.mapping_status == "Active",
            or_(DomainMapping.effective_from.is_(None), DomainMapping.effective_from <= now),
        ))
        if any(c.provider == rules.CERTIFICATE_ACME for c in certificates):
            acme_domains.append(domain.domain_name)
        usable = next((c for c in certificates if c.certificate_status in USABLE_CERTIFICATE), None)
        if not mapping and domain.domain_name not in acme_domains:
            continue
        site = Site(host=domain.domain_name)
        if mapping:
            site.force_https = mapping.force_https or mapping.ssl_required
            if mapping.routing_strategy == rules.ROUTING_REDIRECT:
                site.root_redirect = mapping.target_route
        if usable and mapping:
            try:
                site.fullchain, site.private_key = _tls_material(usable, domain.domain_name)
                site.certificate_id = usable.id
            except Exception:
                # Never logs the exception text, which could quote key material.
                logger.error("The certificate for %s could not be prepared", domain.domain_name)
                site.fullchain = site.private_key = site.certificate_id = None
        sites.append(site)
    return render_files(sites, acme_domains)


async def run_once() -> None:
    # Upkeep has no signed-in tenant and must see every tenant's domains.
    set_rls_context([], bypass=True)
    async with AsyncWriteSessionLocal() as db:
        await expire_stale_claims(db)
        await recheck_verified_domains(db)
        await refresh_certificates(db)
        await db.commit()
        files = await build_gateway_files(db)
    write_candidate(files)


async def white_label_loop() -> None:
    while True:
        await asyncio.sleep(TICK_SECONDS)
        try:
            await run_once()
        except Exception:
            logger.exception("White-label upkeep failed")
