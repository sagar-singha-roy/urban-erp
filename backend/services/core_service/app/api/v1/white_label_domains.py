"""ADM-T04: custom domains, certificates and domain mappings."""
import datetime
import secrets
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.white_label import SUPER_ADMIN, add_audit, available_services, operator_of, require_tenant
from app.core import certificates as certs
from app.core import white_label_rules as rules
from app.core.auth import ensure_tenant_access, require_roles
from app.core.domain_verification import verification_instructions, verify_domain
from app.core.gateway_sync import routing_status
from app.db.models import DomainMapping, TenantCertificate, TenantDomain
from app.db.session import get_read_db, get_write_db
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import (
    CertificateOut, CertificateUpdate, DomainCreate, DomainOut, DomainUpdate, MappingOut, MappingPayload, PagedResponse, RoutingStatus,
)

router = APIRouter(prefix="/white-label", tags=["ADM-T04 White-Labelling & Domain Management"], dependencies=[Depends(require_roles(["super_admin"]))])

CLAIM_DAYS = 7
DOMAIN_TAKEN = "This domain is already held by another tenant."


def _domain_out(domain: TenantDomain) -> DomainOut:
    out = DomainOut.model_validate(domain)
    out.verification_instructions = verification_instructions(domain.verification_method, domain.domain_name, domain.verification_token)
    return out


async def _get_domain(db: AsyncSession, domain_id: str, user: dict) -> TenantDomain:
    domain = await db.scalar(select(TenantDomain).where(TenantDomain.id == domain_id))
    if not domain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Domain not found")
    await ensure_tenant_access(domain.tenant_id, user, db)
    return domain


async def _held_by_other_tenant(db: AsyncSession, name: str, tenant_id: str) -> bool:
    """True when another tenant holds this name, a parent of it, or a host beneath it."""
    held = await db.scalar(select(TenantDomain.id).where(
        TenantDomain.verification_status == "Verified",
        TenantDomain.tenant_id != tenant_id,
        or_(TenantDomain.domain_name.in_(rules.related_domains(name)), TenantDomain.domain_name.like(f"%.{name}")),
    ).limit(1))
    return bool(held)


async def _clear_other_primary(db: AsyncSession, tenant_id: str, keep_id: Optional[str]) -> None:
    statement = update(TenantDomain).where(TenantDomain.tenant_id == tenant_id, TenantDomain.is_primary.is_(True))
    if keep_id:
        statement = statement.where(TenantDomain.id != keep_id)
    await db.execute(statement.values(is_primary=False))


@router.get("/domains", response_model=PagedResponse[DomainOut])
async def list_domains(
    search: Optional[str] = Query(None),
    tenant_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if tenant_id:
        conditions.append(TenantDomain.tenant_id == tenant_id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(TenantDomain.domain_name.ilike(term), TenantDomain.tenant_id.ilike(term)))
    total = await db.scalar(select(func.count(TenantDomain.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(TenantDomain).where(*conditions).order_by(TenantDomain.domain_name).offset(skip).limit(limit))).all()
    return PagedResponse(data=[_domain_out(r) for r in rows], total=total)


@router.post("/domains", response_model=ApiResponse[DomainOut], status_code=status.HTTP_201_CREATED)
async def create_domain(payload: DomainCreate, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    tenant_id = await require_tenant(db, payload.tenant_id, user)
    if await _held_by_other_tenant(db, payload.domain_name, tenant_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DOMAIN_TAKEN)
    if payload.is_primary:
        await _clear_other_primary(db, tenant_id, None)
    # A claim proves nothing until verified, so it holds the name for nobody.
    domain = TenantDomain(
        **{**payload.model_dump(), "tenant_id": tenant_id},
        verification_status="Pending",
        verification_token=secrets.token_hex(32),
        claim_expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=CLAIM_DAYS),
        domain_status="Pending",
        created_by=operator_of(user),
    )
    db.add(domain)
    add_audit(db, tenant_id, "DOMAIN_CLAIMED", user, f"Claimed {payload.domain_name}; awaiting ownership verification.")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This tenant has already claimed this domain.")
    return ApiResponse(data=_domain_out(domain))


@router.put("/domains/{domain_id}", response_model=ApiResponse[DomainOut])
async def update_domain(domain_id: str, payload: DomainUpdate, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    domain = await _get_domain(db, domain_id, user)
    if payload.domain_status == "Active" and domain.verification_status != "Verified":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Verify ownership of this domain before activating it.")
    if payload.is_primary:
        await _clear_other_primary(db, domain.tenant_id, domain.id)
    for field, value in payload.model_dump().items():
        setattr(domain, field, value)
    add_audit(db, domain.tenant_id, "DOMAIN_UPDATED", user, f"{domain.domain_name} saved as {payload.domain_status}.")
    await db.commit()
    return ApiResponse(data=_domain_out(domain))


@router.post("/domains/{domain_id}/verify", response_model=ApiResponse[DomainOut])
async def verify_domain_ownership(domain_id: str, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    domain = await _get_domain(db, domain_id, user)
    now = datetime.datetime.utcnow()
    if domain.verification_status == "Expired":
        # A lapsed claim starts again with a new token, so an old DNS record cannot complete it.
        domain.verification_token = secrets.token_hex(32)
        domain.verification_status = "Pending"
        domain.claim_expires_at = now + datetime.timedelta(days=CLAIM_DAYS)
        domain.last_check_message = "The claim had expired. Publish the new token, then verify again."
        await db.commit()
        return ApiResponse(data=_domain_out(domain))
    if await _held_by_other_tenant(db, domain.domain_name, domain.tenant_id):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DOMAIN_TAKEN)
    result = await verify_domain(domain.domain_name, domain.verification_method, domain.verification_token)
    domain.last_checked_at = now
    domain.last_check_message = result.message[:255]
    if result.verified:
        domain.verification_status = "Verified"
        domain.verified_at = now
        domain.claim_expires_at = None
        add_audit(db, domain.tenant_id, "DOMAIN_VERIFIED", user, f"Ownership of {domain.domain_name} verified by {domain.verification_method}.")
    elif result.conclusive and domain.verification_status != "Verified":
        domain.verification_status = "Failed"
    try:
        await db.commit()
    except IntegrityError:
        # Two tenants verified at once. The unique index let exactly one of them win.
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=DOMAIN_TAKEN)
    return ApiResponse(data=_domain_out(domain))


async def _certificate_out(db: AsyncSession, certificate: TenantCertificate) -> CertificateOut:
    domain_name = await db.scalar(select(TenantDomain.domain_name).where(TenantDomain.id == certificate.domain_id))
    out = CertificateOut.model_validate(certificate)
    out.domain_name = domain_name or ""
    out.has_private_key = bool(await db.scalar(select(TenantCertificate.private_key_encrypted.is_not(None)).where(TenantCertificate.id == certificate.id)))
    return out


@router.get("/certificates", response_model=PagedResponse[CertificateOut])
async def list_certificates(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    base = select(TenantCertificate).join(TenantDomain, TenantCertificate.domain_id == TenantDomain.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        base = base.where(or_(TenantDomain.domain_name.ilike(term), TenantCertificate.tenant_id.ilike(term), TenantCertificate.provider.ilike(term)))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (await db.scalars(base.order_by(TenantCertificate.created_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[await _certificate_out(db, r) for r in rows], total=total)


async def _read_text(upload: Optional[UploadFile]) -> str:
    if not upload:
        return ""
    data = await upload.read(certs.MAX_PEM_BYTES + 1)
    if len(data) > certs.MAX_PEM_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certificate files must be 64 KB or smaller.")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certificate files must be PEM text.") from None


@router.post("/certificates", response_model=ApiResponse[CertificateOut], status_code=status.HTTP_201_CREATED)
async def create_certificate(
    domain_id: str = Form(..., alias="domainId"),
    provider: str = Form(...),
    certificate_type: str = Form(..., alias="certificateType"),
    auto_renewal: bool = Form(False, alias="autoRenewal"),
    renewal_notification_days: int = Form(30, alias="renewalNotificationDays", ge=1, le=120),
    private_key: Optional[str] = Form(None, alias="privateKey"),
    certificate: Optional[UploadFile] = File(None),
    certificate_chain: Optional[UploadFile] = File(None, alias="certificateChain"),
    db: AsyncSession = Depends(get_write_db),
    user: dict = SUPER_ADMIN,
):
    domain = await _get_domain(db, domain_id, user)
    if domain.verification_status != "Verified":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Verify ownership of this domain first.")
    if provider not in rules.CERTIFICATE_PROVIDERS or certificate_type not in rules.CERTIFICATE_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown certificate provider or type")
    record = TenantCertificate(
        tenant_id=domain.tenant_id, domain_id=domain.id, provider=provider, certificate_type=certificate_type,
        renewal_notification_days=renewal_notification_days, created_by=operator_of(user),
    )
    if provider == rules.CERTIFICATE_MANUAL:
        certificate_pem = await _read_text(certificate)
        chain_pem = await _read_text(certificate_chain)
        if not certificate_pem or not private_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A manual upload needs the certificate and its private key.")
        try:
            parsed = certs.validate_upload(certificate_pem, private_key, chain_pem, domain.domain_name)
            record.private_key_encrypted = certs.encrypt_private_key(private_key)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from None
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from None
        record.certificate_pem = certificate_pem
        record.certificate_chain_pem = chain_pem or None
        record.expiry_date = parsed.expiry
        record.auto_renewal = False
        record.certificate_status = certs.status_for_expiry(parsed.expiry, renewal_notification_days)
        record.last_validation_at = datetime.datetime.utcnow()
    else:
        if certificate_type == "Wildcard":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Let's Encrypt issues this domain's certificate only. Upload wildcard certificates manually.")
        record.auto_renewal = auto_renewal
        record.certificate_status = "Pending Issuance"
        record.status_message = "Waiting for the certificate manager to issue this certificate."
    db.add(record)
    add_audit(db, domain.tenant_id, "CERTIFICATE_ADDED", user, f"{provider} certificate added for {domain.domain_name}.")
    await db.commit()
    return ApiResponse(data=await _certificate_out(db, record))


@router.put("/certificates/{certificate_id}", response_model=ApiResponse[CertificateOut])
async def update_certificate(certificate_id: str, payload: CertificateUpdate, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    record = await db.scalar(select(TenantCertificate).where(TenantCertificate.id == certificate_id))
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found")
    await ensure_tenant_access(record.tenant_id, user, db)
    record.auto_renewal = payload.auto_renewal and record.provider == rules.CERTIFICATE_ACME
    record.renewal_notification_days = payload.renewal_notification_days
    if record.expiry_date:
        record.certificate_status = certs.status_for_expiry(record.expiry_date, record.renewal_notification_days)
    add_audit(db, record.tenant_id, "CERTIFICATE_UPDATED", user, "Certificate renewal settings changed.")
    await db.commit()
    return ApiResponse(data=await _certificate_out(db, record))


async def _activation_blocker(db: AsyncSession, domain: TenantDomain, payload: MappingPayload) -> Optional[str]:
    if domain.verification_status != "Verified" or domain.domain_status != "Active":
        return "The domain must be verified and active before this mapping can go live."
    if payload.ssl_required:
        certificate = await db.scalar(select(TenantCertificate.id).where(
            TenantCertificate.domain_id == domain.id, TenantCertificate.certificate_status.in_(["Active", "Expiring Soon"]),
        ).limit(1))
        if not certificate:
            return "This mapping requires SSL, so the domain needs a valid certificate first."
    return None


async def _save_mapping(db: AsyncSession, mapping: DomainMapping, payload: MappingPayload, user: dict) -> DomainMapping:
    tenant_id = await require_tenant(db, payload.tenant_id, user)
    domain = await _get_domain(db, payload.domain_id, user)
    # A tenant can only route a domain it holds.
    if domain.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This domain does not belong to the selected tenant.")
    if payload.target_service not in await available_services(db):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown target service")
    if payload.mapping_status == "Active":
        blocker = await _activation_blocker(db, domain, payload)
        if blocker:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=blocker)
    if payload.is_primary:
        await db.execute(update(DomainMapping).where(DomainMapping.tenant_id == tenant_id, DomainMapping.id != mapping.id).values(is_primary=False))
    for field, value in payload.model_dump().items():
        setattr(mapping, field, value)
    mapping.tenant_id = tenant_id
    if mapping.effective_from:
        mapping.effective_from = mapping.effective_from.replace(tzinfo=None)
    add_audit(db, tenant_id, "DOMAIN_MAPPING_SAVED", user, f"Mapping {payload.mapping_name} for {domain.domain_name} saved as {payload.mapping_status}.")
    return mapping


async def _mapping_out(db: AsyncSession, mapping: DomainMapping) -> MappingOut:
    out = MappingOut.model_validate(mapping)
    out.domain_name = await db.scalar(select(TenantDomain.domain_name).where(TenantDomain.id == mapping.domain_id)) or ""
    return out


@router.get("/mappings", response_model=PagedResponse[MappingOut])
async def list_mappings(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    base = select(DomainMapping).join(TenantDomain, DomainMapping.domain_id == TenantDomain.id)
    if search and search.strip():
        term = f"%{search.strip()}%"
        base = base.where(or_(DomainMapping.mapping_name.ilike(term), TenantDomain.domain_name.ilike(term), DomainMapping.tenant_id.ilike(term)))
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (await db.scalars(base.order_by(DomainMapping.mapping_name).offset(skip).limit(limit))).all()
    return PagedResponse(data=[await _mapping_out(db, r) for r in rows], total=total)


@router.post("/mappings", response_model=ApiResponse[MappingOut], status_code=status.HTTP_201_CREATED)
async def create_mapping(payload: MappingPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    mapping = DomainMapping(created_by=operator_of(user))
    await _save_mapping(db, mapping, payload, user)
    db.add(mapping)
    return await _commit_mapping(db, mapping)


@router.put("/mappings/{mapping_id}", response_model=ApiResponse[MappingOut])
async def update_mapping(mapping_id: str, payload: MappingPayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    mapping = await db.scalar(select(DomainMapping).where(DomainMapping.id == mapping_id))
    if not mapping:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapping not found")
    await ensure_tenant_access(mapping.tenant_id, user, db)
    await _save_mapping(db, mapping, payload, user)
    return await _commit_mapping(db, mapping)


async def _commit_mapping(db: AsyncSession, mapping: DomainMapping) -> ApiResponse[MappingOut]:
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This domain already has an active mapping.")
    return ApiResponse(data=await _mapping_out(db, mapping))


@router.get("/routing-status", response_model=ApiResponse[RoutingStatus])
async def get_routing_status():
    state = routing_status()
    return ApiResponse(data=RoutingStatus(applied_version=state["appliedVersion"], pending_version=state["pendingVersion"], last_error=state["lastError"]))
