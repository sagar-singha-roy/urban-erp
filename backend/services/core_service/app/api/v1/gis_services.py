"""ADM-A04: approved remote services, server-side WFS sync and boundary imports."""
import ipaddress
import json
import socket
from typing import Optional
from urllib.parse import urlencode, urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.gis import (
    MAX_IMPORT_FEATURES, _authorized_layer, _authorized_ulb, _srid, approved_service_urls, declared_crs, features_of, manage_layers,
    replace_features, url_is_approved, VIEW_ROLES,
)
from app.api.v1.white_label import add_audit, operator_of
from app.core.auth import get_current_user, is_super_admin, require_roles, tenant_scope_filter
from app.core.config import settings
from app.db.models import GisApprovedService, Tenant
from app.db.session import get_read_db, get_write_db
from app.schemas.gis import GisBoundaryImportPayload, GisImportResult, GisServicePayload, GisServiceResponse
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

router = APIRouter(prefix="/executive/gis", tags=["ADM-A04 Spatial GIS Multi-City Viewer"], dependencies=[Depends(require_roles(VIEW_ROLES))])

MAX_WFS_BYTES = 50 * 1024 * 1024


def host_is_public(host: str) -> bool:
    """Tenants supply these addresses, so the server must not be pointed at its own network."""
    try:
        infos = socket.getaddrinfo(host, None)
    except OSError:
        return False
    addresses = {info[4][0] for info in infos}
    return bool(addresses) and all(ipaddress.ip_address(a).is_global for a in addresses)


def normalize_service_url(url: str) -> str:
    parsed = urlparse(url.strip())
    allowed = {"https", "http"} if settings.is_development else {"https"}
    if parsed.scheme not in allowed or not parsed.hostname:
        raise HTTPException(status_code=422, detail="A service address must be a valid https address.")
    if "@" in parsed.netloc or parsed.query or parsed.fragment:
        raise HTTPException(status_code=422, detail="A service address cannot contain a password or a query.")
    if not settings.is_development and not host_is_public(parsed.hostname):
        raise HTTPException(status_code=422, detail="This service address does not resolve to a public address.")
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"


def _service_out(row: GisApprovedService) -> GisServiceResponse:
    return GisServiceResponse(id=row.id, tenantId=row.tenant_id, serviceName=row.service_name, baseUrl=row.base_url, isActive=row.is_active)


@router.get("/services", response_model=PagedResponse[GisServiceResponse])
async def list_services(
    tenantId: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if tenantId:
        conditions.append(GisApprovedService.tenant_id == (await _authorized_ulb(tenantId, user, db)).tenant_id)
    elif not is_super_admin(user):
        conditions.append(GisApprovedService.tenant_id.in_(select(Tenant.tenant_id).where(tenant_scope_filter(user))))
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(GisApprovedService.service_name.ilike(term), GisApprovedService.base_url.ilike(term)))
    total = await db.scalar(select(func.count(GisApprovedService.id)).where(*conditions)) or 0
    rows = (await db.scalars(select(GisApprovedService).where(*conditions).order_by(GisApprovedService.service_name).offset(skip).limit(limit))).all()
    return PagedResponse(total=total, data=[_service_out(r) for r in rows])


@router.post("/services", response_model=ApiResponse[GisServiceResponse], status_code=status.HTTP_201_CREATED)
async def create_service(payload: GisServicePayload, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    tenant = await _authorized_ulb(payload.tenantId, user, db)
    row = GisApprovedService(
        tenant_id=tenant.tenant_id, service_name=payload.serviceName.strip(), base_url=normalize_service_url(payload.baseUrl),
        is_active=payload.isActive, created_by=operator_of(user),
    )
    db.add(row)
    add_audit(db, tenant.tenant_id, "GIS_SERVICE_APPROVED", user, f"Approved {row.base_url}.")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This service is already approved for this ULB.")
    return ApiResponse(data=_service_out(row))


@router.put("/services/{service_id}", response_model=ApiResponse[GisServiceResponse])
async def update_service(service_id: str, payload: GisServicePayload, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    row = await db.scalar(select(GisApprovedService).where(GisApprovedService.id == service_id))
    if not row:
        raise HTTPException(status_code=404, detail="Service not found.")
    await _authorized_ulb(row.tenant_id, user, db)
    row.service_name = payload.serviceName.strip()
    row.base_url = normalize_service_url(payload.baseUrl)
    row.is_active = payload.isActive
    add_audit(db, row.tenant_id, "GIS_SERVICE_UPDATED", user, f"{row.base_url} saved as {'active' if row.is_active else 'inactive'}.")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="This service is already approved for this ULB.")
    return ApiResponse(data=_service_out(row))


async def fetch_wfs(service_url: str, identifier: str) -> dict:
    """Redirects are not followed, so an approved service cannot send this request somewhere else."""
    hostname = urlparse(service_url).hostname or ""
    if not settings.is_development and not host_is_public(hostname):
        raise HTTPException(status_code=502, detail="This service no longer resolves to a public address.")
    query = urlencode({"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": identifier, "outputFormat": "application/json", "srsName": "EPSG:4326", "count": MAX_IMPORT_FEATURES})
    separator = "&" if "?" in service_url else "?"
    body = bytearray()
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=False, trust_env=False) as client:
            async with client.stream("GET", f"{service_url}{separator}{query}") as response:
                if response.status_code != 200:
                    raise HTTPException(status_code=502, detail=f"The WFS service answered {response.status_code}.")
                async for chunk in response.aiter_bytes():
                    body.extend(chunk)
                    if len(body) > MAX_WFS_BYTES:
                        raise HTTPException(status_code=502, detail="The WFS response is too large.")
    except httpx.HTTPError:
        raise HTTPException(status_code=502, detail="The WFS service could not be reached.")
    try:
        return json.loads(bytes(body))
    except ValueError:
        raise HTTPException(status_code=502, detail="The WFS service did not return GeoJSON.")


@router.post("/layers/{layer_id}/sync", response_model=ApiResponse[GisImportResult])
async def sync_wfs_layer(layer_id: str, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    """Copies a WFS layer into PostGIS, cut to this ULB's boundary, so the map cannot show a neighbour's data."""
    layer = await _authorized_layer(layer_id, user, db)
    if layer.data_source != "WFS":
        raise HTTPException(status_code=409, detail="Only WFS layers are synchronised.")
    urls = await approved_service_urls(db, [layer.tenant_id])
    if not url_is_approved(layer.service_url, urls.get(layer.tenant_id, [])):
        raise HTTPException(status_code=409, detail="This layer's service is not on the approved list.")
    has_boundary = await db.scalar(text("SELECT count(*) FROM wards WHERE tenant_id = :tenant AND geom IS NOT NULL"), {"tenant": layer.tenant_id})
    if not has_boundary:
        raise HTTPException(status_code=409, detail="Import this ULB's ward boundaries first, because WFS data is cut to them.")
    collection = await fetch_wfs(layer.service_url, layer.layer_identifier)
    result = await replace_features(db, layer, features_of(collection), 4326, clip=True)
    add_audit(db, layer.tenant_id, "GIS_LAYER_SYNCED", user, f"{result.imported} features stored for {layer.layer_code}, {result.rejected} outside the ULB or invalid.")
    await db.commit()
    return ApiResponse(data=result)


LEVEL_UPDATES = {
    "Ward": (
        "UPDATE wards SET boundary_geometry = CAST(ST_AsGeoJSON(g) AS json) FROM s "
        "WHERE tenant_id = :tenant AND (CAST(ward_number AS text) = :match OR ward_code = :match OR ward_name = :match)"
    ),
    "Zone": "UPDATE zones SET geom = g FROM s WHERE tenant_id = :tenant AND (code = :match OR name = :match)",
    "Parcel": (
        "UPDATE property_parcels SET boundary_geom = g, survey_status = COALESCE(CAST(:survey AS varchar), survey_status) FROM s "
        "WHERE tenant_id = :tenant AND (ulpin = :match OR survey_number = :match)"
    ),
}


@router.post("/boundaries/import", response_model=ApiResponse[GisImportResult])
async def import_boundaries(payload: GisBoundaryImportPayload, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    """Attaches boundaries to existing wards, zones or parcels of this ULB, matched on a property of each feature."""
    tenant = await _authorized_ulb(payload.tenantId, user, db)
    update = LEVEL_UPDATES.get(payload.level)
    if not update:
        raise HTTPException(status_code=422, detail="Boundaries can be imported for Ward, Zone or Parcel.")
    srid = _srid(payload.sourceCrs)
    named = declared_crs(payload.featureCollection)
    if named and named != payload.sourceCrs:
        raise HTTPException(status_code=422, detail=f"This file says it is in {named}, but {payload.sourceCrs} was selected.")
    statement = text(
        "WITH s AS (SELECT ST_Multi(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(CAST(:geometry AS text)), CAST(:srid AS integer)), 4326)) AS g) "
        f"{update} AND ST_IsValid(g) AND GeometryType(g) = 'MULTIPOLYGON' AND ST_XMin(g) >= -180 AND ST_XMax(g) <= 180 AND ST_YMin(g) >= -90 AND ST_YMax(g) <= 90"
    )
    imported = rejected = 0
    for feature in features_of(payload.featureCollection):
        properties = (feature.get("properties") or {}) if isinstance(feature, dict) else {}
        match = properties.get(payload.matchField)
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if match is None or not geometry:
            rejected += 1
            continue
        params = {"geometry": json.dumps(geometry), "srid": srid, "tenant": tenant.tenant_id, "match": str(match)}
        if payload.level == "Parcel":
            params["survey"] = properties.get("surveyStatus")
        try:
            async with db.begin_nested():
                result = await db.execute(statement, params)
            imported += 1 if result.rowcount else 0
            rejected += 0 if result.rowcount else 1
        except Exception:
            rejected += 1
    add_audit(db, tenant.tenant_id, "GIS_BOUNDARIES_IMPORTED", user, f"{imported} {payload.level} boundaries imported, {rejected} rejected.")
    await db.commit()
    return ApiResponse(data=GisImportResult(imported=imported, rejected=rejected))
