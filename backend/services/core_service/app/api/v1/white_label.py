"""ADM-T04: branding profiles, logo assets and the public branding a site needs before sign-in."""
import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import white_label_rules as rules
from app.core.auth import ensure_tenant_access, require_roles
from app.core.config import PLATFORM_ULB_TYPE, settings
from app.core.quota_service import QuotaExceeded, reserve_storage
from app.core.tenant_context import set_rls_context
from app.db.models import (
    BrandingAssetFile, BrandingAssetSet, BrandingProfile, MicroserviceRegistryModel, StateTenant, Tenant,
    TenantAuditLog, TenantDomain,
)
from app.db.session import AsyncReadSessionLocal, get_read_db, get_write_db
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import (
    AssetFileOut, AssetSetOut, AssetSetUpdate, BrandingProfileOut, BrandingProfilePayload, PagedResponse, PublicBranding,
    TenantOption, WhiteLabelOptions,
)

SUPER_ADMIN = Depends(require_roles(["super_admin"]))
router = APIRouter(prefix="/white-label", tags=["ADM-T04 White-Labelling & Domain Management"], dependencies=[SUPER_ADMIN])
public_router = APIRouter(prefix="/white-label/public", tags=["ADM-T04 Public Branding"])

_FILE_TYPES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp", "image/x-icon": "ico"}

# Gateway targets that exist on every deployment; module services come from the fleet registry.
PLATFORM_SERVICES = ["console", "core"]


def operator_of(user: dict) -> str:
    return str(user.get("preferred_username") or user.get("email") or "system")[:100]


def add_audit(db: AsyncSession, tenant_id: str, action: str, user: dict, details: str) -> None:
    db.add(TenantAuditLog(tenant_id=tenant_id, action=action[:50], performed_by=operator_of(user), details=details))


async def tenant_exists(db: AsyncSession, tenant_id: str) -> bool:
    if await db.scalar(select(Tenant.tenant_id).where(Tenant.tenant_id == tenant_id)):
        return True
    return bool(await db.scalar(select(StateTenant.tenant_id).where(StateTenant.tenant_id == tenant_id)))


async def require_tenant(db: AsyncSession, tenant_id: str, user: dict) -> str:
    normalized = tenant_id.strip()
    await ensure_tenant_access(normalized, user, db)
    if not await tenant_exists(db, normalized):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return normalized


async def available_services(db: AsyncSession) -> List[str]:
    registered = (await db.scalars(select(MicroserviceRegistryModel.service_code))).all()
    return sorted(set(PLATFORM_SERVICES) | set(registered))


@router.get("/options", response_model=ApiResponse[WhiteLabelOptions])
async def get_options(db: AsyncSession = Depends(get_read_db)):
    return ApiResponse(data=WhiteLabelOptions(
        tenant_levels=rules.TENANT_LEVELS, record_statuses=rules.RECORD_STATUSES, font_families=rules.FONT_FAMILIES,
        logo_types=rules.LOGO_TYPES, domain_types=rules.DOMAIN_TYPES, dns_providers=rules.DNS_PROVIDERS,
        dns_record_types=rules.DNS_RECORD_TYPES, verification_methods=rules.VERIFICATION_METHODS,
        domain_statuses=rules.DOMAIN_STATUSES, certificate_providers=rules.CERTIFICATE_PROVIDERS,
        certificate_types=rules.CERTIFICATE_TYPES, target_applications=rules.TARGET_APPLICATIONS,
        target_services=await available_services(db), routing_strategies=rules.ROUTING_STRATEGIES,
    ))


@router.get("/tenants", response_model=ApiResponse[List[TenantOption]])
async def list_tenant_options(
    search: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    states = select(StateTenant).order_by(StateTenant.state_name).limit(limit)
    ulbs = select(Tenant).order_by(Tenant.name).limit(limit)
    if search and search.strip():
        term = f"%{search.strip()}%"
        states = states.where(or_(StateTenant.state_name.ilike(term), StateTenant.tenant_id.ilike(term)))
        ulbs = ulbs.where(or_(Tenant.name.ilike(term), Tenant.tenant_id.ilike(term)))
    state_rows = (await db.scalars(states)).all()
    options = [TenantOption(tenant_id=s.tenant_id, name=s.state_name, tenant_level="State", state_tenant_id=s.tenant_id) for s in state_rows]
    # ULBs may record their state by code only, so look its tenant up from the code.
    state_ids = dict((await db.execute(select(StateTenant.state_code, StateTenant.tenant_id))).all())
    options += [
        TenantOption(tenant_id=u.tenant_id, name=u.name, tenant_level="ULB",
                     state_tenant_id=u.parent_state_tenant_id or state_ids.get(u.state_code) or u.state_code)
        for u in (await db.scalars(ulbs)).all()
        if u.ulb_type != PLATFORM_ULB_TYPE
    ]
    return ApiResponse(data=options)


async def _resolve_profile_tenant(db: AsyncSession, payload: BrandingProfilePayload, user: dict) -> str:
    state_id = await require_tenant(db, payload.state_tenant_id, user)
    if payload.tenant_level == "State":
        return state_id
    ulb_id = await require_tenant(db, payload.ulb_tenant_id or "", user)
    ulb = await db.scalar(select(Tenant).where(Tenant.tenant_id == ulb_id))
    state = await db.scalar(select(StateTenant).where(StateTenant.tenant_id == state_id))
    if not ulb or not state or (ulb.parent_state_tenant_id != state_id and ulb.state_code != state.state_code):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This ULB does not belong to the selected state")
    return ulb_id


async def _deactivate_other_profiles(db: AsyncSession, tenant_id: str, keep_id: Optional[str]) -> None:
    statement = update(BrandingProfile).where(BrandingProfile.tenant_id == tenant_id, BrandingProfile.branding_status == "Active")
    if keep_id:
        statement = statement.where(BrandingProfile.id != keep_id)
    await db.execute(statement.values(branding_status="Inactive"))


@router.get("/branding", response_model=PagedResponse[BrandingProfileOut])
async def list_branding_profiles(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(BrandingProfile.profile_name.ilike(term), BrandingProfile.display_name.ilike(term), BrandingProfile.tenant_id.ilike(term)))
    total = await db.scalar(select(func.count(BrandingProfile.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(BrandingProfile).where(*conditions).order_by(BrandingProfile.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=[BrandingProfileOut.model_validate(r) for r in rows], total=total)


def _apply_profile(profile: BrandingProfile, payload: BrandingProfilePayload, tenant_id: str) -> None:
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    profile.tenant_id = tenant_id
    if payload.tenant_level == "State":
        profile.ulb_tenant_id = None


@router.post("/branding", response_model=ApiResponse[BrandingProfileOut], status_code=status.HTTP_201_CREATED)
async def create_branding_profile(payload: BrandingProfilePayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    tenant_id = await _resolve_profile_tenant(db, payload, user)
    profile = BrandingProfile(created_by=operator_of(user))
    _apply_profile(profile, payload, tenant_id)
    if payload.branding_status == "Active":
        await _deactivate_other_profiles(db, tenant_id, None)
    db.add(profile)
    add_audit(db, tenant_id, "BRANDING_CREATED", user, f"Branding profile {payload.profile_name} saved as {payload.branding_status}.")
    await db.commit()
    return ApiResponse(data=BrandingProfileOut.model_validate(profile))


@router.put("/branding/{profile_id}", response_model=ApiResponse[BrandingProfileOut])
async def update_branding_profile(profile_id: str, payload: BrandingProfilePayload, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    profile = await db.scalar(select(BrandingProfile).where(BrandingProfile.id == profile_id))
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branding profile not found")
    tenant_id = await _resolve_profile_tenant(db, payload, user)
    if payload.branding_status == "Active":
        await _deactivate_other_profiles(db, tenant_id, profile.id)
    _apply_profile(profile, payload, tenant_id)
    add_audit(db, tenant_id, "BRANDING_UPDATED", user, f"Branding profile {payload.profile_name} saved as {payload.branding_status}.")
    await db.commit()
    return ApiResponse(data=BrandingProfileOut.model_validate(profile))


async def _asset_out(db: AsyncSession, asset_sets: List[BrandingAssetSet]) -> List[AssetSetOut]:
    ids = [a.id for a in asset_sets]
    by_set: Dict[str, List[AssetFileOut]] = {}
    if ids:
        columns = (BrandingAssetFile.asset_set_id, BrandingAssetFile.id, BrandingAssetFile.file_kind, BrandingAssetFile.content_type, BrandingAssetFile.size_bytes)
        for row in (await db.execute(select(*columns).where(BrandingAssetFile.asset_set_id.in_(ids)))).all():
            by_set.setdefault(row.asset_set_id, []).append(AssetFileOut(id=row.id, file_kind=row.file_kind, content_type=row.content_type, size_bytes=row.size_bytes))
    return [
        AssetSetOut(id=a.id, tenant_id=a.tenant_id, logo_type=a.logo_type, alt_text=a.alt_text, effective_from=a.effective_from,
                    asset_status=a.asset_status, files=by_set.get(a.id, []), updated_at=a.updated_at)
        for a in asset_sets
    ]


@router.get("/assets", response_model=PagedResponse[AssetSetOut])
async def list_asset_sets(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(BrandingAssetSet.tenant_id.ilike(term), BrandingAssetSet.logo_type.ilike(term), BrandingAssetSet.alt_text.ilike(term)))
    total = await db.scalar(select(func.count(BrandingAssetSet.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(BrandingAssetSet).where(*conditions).order_by(BrandingAssetSet.updated_at.desc()).offset(skip).limit(limit))).all()
    return PagedResponse(data=await _asset_out(db, list(rows)), total=total)


@router.post("/assets", response_model=ApiResponse[AssetSetOut], status_code=status.HTTP_201_CREATED)
async def create_asset_set(
    tenant_id: str = Form(..., alias="tenantId"),
    logo_type: str = Form(..., alias="logoType"),
    alt_text: str = Form(..., alias="altText", min_length=1, max_length=255),
    asset_status: str = Form("Draft", alias="assetStatus"),
    effective_from: Optional[datetime.datetime] = Form(None, alias="effectiveFrom"),
    logo: UploadFile = File(...),
    emblem: Optional[UploadFile] = File(None),
    favicon: Optional[UploadFile] = File(None),
    login_banner: Optional[UploadFile] = File(None, alias="loginBanner"),
    header_logo: Optional[UploadFile] = File(None, alias="headerLogo"),
    footer_logo: Optional[UploadFile] = File(None, alias="footerLogo"),
    watermark: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_write_db),
    user: dict = SUPER_ADMIN,
):
    tenant = await require_tenant(db, tenant_id, user)
    if logo_type not in rules.LOGO_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown logo type")
    if asset_status not in rules.RECORD_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown asset status")
    if logo_type == "Official Emblem" and not emblem:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="An emblem file is required for an Official Emblem")
    uploads = {"logo": logo, "emblem": emblem, "favicon": favicon, "login_banner": login_banner,
               "header_logo": header_logo, "footer_logo": footer_logo, "watermark": watermark}
    asset_set = BrandingAssetSet(tenant_id=tenant, logo_type=logo_type, alt_text=alt_text.strip(), asset_status=asset_status,
                                 effective_from=effective_from.replace(tzinfo=None) if effective_from else None, created_by=operator_of(user))
    db.add(asset_set)
    await db.flush()
    for kind, upload in uploads.items():
        if not upload:
            continue
        # Reads one byte past the limit, so an oversized file is refused without loading all of it.
        data = await upload.read(rules.MAX_ASSET_BYTES + 1)
        try:
            content_type, digest = rules.validate_asset(data)
        except ValueError as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{kind.replace('_', ' ').title()}: {exc}")
        try:
            await reserve_storage(db, tenant_id=tenant, storage_type="Image Storage", module_code="ADM", object_name=upload.filename or kind,
                                  size_bytes=len(data), file_type=_FILE_TYPES[content_type])
        except QuotaExceeded as exc:
            await db.rollback()
            raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc))
        db.add(BrandingAssetFile(tenant_id=tenant, asset_set_id=asset_set.id, file_kind=kind, content_type=content_type,
                                 size_bytes=len(data), sha256=digest, data=data))
    add_audit(db, tenant, "BRANDING_ASSET_UPLOADED", user, f"{logo_type} assets uploaded as {asset_status}.")
    await db.flush()
    result = (await _asset_out(db, [asset_set]))[0]
    await db.commit()
    return ApiResponse(data=result)


@router.put("/assets/{asset_set_id}", response_model=ApiResponse[AssetSetOut])
async def update_asset_set(asset_set_id: str, payload: AssetSetUpdate, db: AsyncSession = Depends(get_write_db), user: dict = SUPER_ADMIN):
    asset_set = await db.scalar(select(BrandingAssetSet).where(BrandingAssetSet.id == asset_set_id))
    if not asset_set:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assets not found")
    await ensure_tenant_access(asset_set.tenant_id, user, db)
    asset_set.alt_text = payload.alt_text.strip()
    asset_set.effective_from = payload.effective_from.replace(tzinfo=None) if payload.effective_from else None
    asset_set.asset_status = payload.asset_status
    add_audit(db, asset_set.tenant_id, "BRANDING_ASSET_UPDATED", user, f"{asset_set.logo_type} assets saved as {payload.asset_status}.")
    await db.commit()
    return ApiResponse(data=(await _asset_out(db, [asset_set]))[0])


def _image_response(row: BrandingAssetFile) -> Response:
    return Response(content=row.data, media_type=row.content_type, headers={
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; sandbox",
        "Cache-Control": "public, max-age=300",
    })


@router.get("/assets/files/{file_id}")
async def preview_asset_file(file_id: str, db: AsyncSession = Depends(get_read_db)):
    row = await db.scalar(select(BrandingAssetFile).where(BrandingAssetFile.id == file_id).options(_load_data()))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return _image_response(row)


def _load_data():
    from sqlalchemy.orm import undefer
    return undefer(BrandingAssetFile.data)


def _request_host(request: Request) -> str:
    return (request.headers.get("host") or "").split(":")[0].strip().lower().rstrip(".")


async def _branding_chain(db: AsyncSession, tenant_id: str) -> List[str]:
    """A ULB uses its own branding, then its state's."""
    chain = [tenant_id]
    ulb = await db.scalar(select(Tenant).where(Tenant.tenant_id == tenant_id))
    if ulb:
        state_id = ulb.parent_state_tenant_id or await db.scalar(select(StateTenant.tenant_id).where(StateTenant.state_code == ulb.state_code))
        if state_id:
            chain.append(state_id)
    return chain


class _PublicSession:
    """Public pages have no signed-in tenant. These queries return active, display-only rows, never a tenant's records."""

    async def __aenter__(self) -> AsyncSession:
        set_rls_context([], bypass=True)
        self.session = AsyncReadSessionLocal()
        return self.session

    async def __aexit__(self, *_):
        await self.session.close()
        set_rls_context([])


@public_router.get("/branding", response_model=ApiResponse[Optional[PublicBranding]])
async def public_branding(request: Request):
    host = _request_host(request)
    async with _PublicSession() as db:
        tenant_id = await db.scalar(select(TenantDomain.tenant_id).where(
            TenantDomain.domain_name == host, TenantDomain.verification_status == "Verified", TenantDomain.domain_status == "Active",
        ))
        if not tenant_id:
            return ApiResponse(data=None)
        chain = await _branding_chain(db, tenant_id)
        profile = None
        for candidate in chain:
            profile = await db.scalar(select(BrandingProfile).where(BrandingProfile.tenant_id == candidate, BrandingProfile.branding_status == "Active"))
            if profile:
                break
        if not profile:
            return ApiResponse(data=None)
        now = datetime.datetime.utcnow()
        assets: Dict[str, str] = {}
        alt_text = None
        for candidate in chain:
            asset_set = await db.scalar(
                select(BrandingAssetSet)
                .where(BrandingAssetSet.tenant_id == candidate, BrandingAssetSet.asset_status == "Active",
                       or_(BrandingAssetSet.effective_from.is_(None), BrandingAssetSet.effective_from <= now))
                .order_by(BrandingAssetSet.updated_at.desc()).limit(1)
            )
            if asset_set:
                alt_text = asset_set.alt_text
                rows = (await db.execute(select(BrandingAssetFile.id, BrandingAssetFile.file_kind).where(BrandingAssetFile.asset_set_id == asset_set.id))).all()
                assets = {row.file_kind: f"{settings.API_V1_STR}/white-label/public/assets/{row.id}" for row in rows}
                break
        return ApiResponse(data=PublicBranding(
            display_name=profile.display_name, tagline=profile.tagline, primary_colour=profile.primary_colour,
            secondary_colour=profile.secondary_colour, accent_colour=profile.accent_colour,
            header_background_colour=profile.header_background_colour, sidebar_background_colour=profile.sidebar_background_colour,
            font_family=profile.font_family, login_page_title=profile.login_page_title, login_page_message=profile.login_page_message,
            footer_text=profile.footer_text, custom_css=profile.custom_css, alt_text=alt_text, assets=assets,
        ))


@public_router.get("/assets/{file_id}")
async def public_asset_file(file_id: str):
    async with _PublicSession() as db:
        row = await db.scalar(
            select(BrandingAssetFile).join(BrandingAssetSet, BrandingAssetFile.asset_set_id == BrandingAssetSet.id)
            .where(BrandingAssetFile.id == file_id, BrandingAssetSet.asset_status == "Active").options(_load_data())
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
        return _image_response(row)
