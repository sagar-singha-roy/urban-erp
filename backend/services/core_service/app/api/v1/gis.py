"""ADM-A04 Spatial GIS Multi-City Viewer.

Geometry is stored in EPSG:4326. Every read and write resolves an authorized ULB first,
and PostgreSQL row-level security applies the same scope again underneath.
"""
import datetime
import json
import re
import uuid
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import distinct, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.white_label import add_audit
from app.core.auth import ensure_tenant_access, get_current_user, is_super_admin, require_roles, tenant_scope_filter
from app.core.config import PLATFORM_ULB_TYPE, settings
from app.db.models import (
    Building,
    GisApprovedService,
    GisFeatureModel,
    GisLayerModel,
    GisWorkspaceModel,
    PropertyParcel,
    PropertyUnit,
    Tenant,
    Ward,
    Zone,
)
from app.db.session import get_read_db, get_write_db
from app.schemas.gis import (
    GisImportPayload,
    GisImportResult,
    GisLayerPayload,
    GisLayerResponse,
    GisOptions,
    GisScopeRow,
    GisWorkspacePayload,
    GisWorkspaceResponse,
)
from app.schemas.tenant import ApiResponse
from app.schemas.white_label import PagedResponse

VIEW_ROLES = ["state_director", "revenue_officer", "town_planner"]
router = APIRouter(prefix="/executive/gis", tags=["ADM-A04 Spatial GIS Multi-City Viewer"], dependencies=[Depends(require_roles(VIEW_ROLES))])
manage_layers = require_roles(["state_director"])

CRS_OPTIONS = {
    "EPSG:4326": "WGS 84 (Latitude / Longitude)",
    "EPSG:3857": "Web Mercator",
    "EPSG:32643": "WGS 84 / UTM Zone 43N",
    "EPSG:32644": "WGS 84 / UTM Zone 44N",
    "EPSG:32645": "WGS 84 / UTM Zone 45N",
    "EPSG:32646": "WGS 84 / UTM Zone 46N",
}
LAYER_CATEGORIES = ["City", "Boundary", "Parcel", "Utility", "Zone", "Road"]
LAYER_TYPES = ["Point", "Line", "Polygon", "Raster"]
DATA_SOURCES = ["PostGIS", "GeoJSON", "WMS", "WFS"]
REMOTE_SOURCES = {"WMS", "WFS"}
LAYER_STATUSES = ["Active", "Draft", "Inactive"]
GEOGRAPHIC_SCOPES = ["All Accessible States", "Selected States", "Selected ULBs", "Custom Extent"]
SURVEY_STATUSES = ["Not Surveyed", "In Progress", "Surveyed", "Verified"]
GEOMETRY_TYPES = {"Point": "'POINT', 'MULTIPOINT'", "Line": "'LINESTRING', 'MULTILINESTRING'", "Polygon": "'POLYGON', 'MULTIPOLYGON'"}
# Validated numeric text only, so a stray value in imported data cannot fail the whole query.
WIDTH_SQL = "CASE WHEN f.properties->>'width' ~ '^[0-9]+(\\.[0-9]+)?$' THEN (f.properties->>'width')::float END"
ULB_REGION_SQL = "(SELECT ST_Union(w.geom) FROM wards w WHERE w.tenant_id = :tenant AND w.geom IS NOT NULL)"
MAX_FEATURES = 5000
MAX_IMPORT_FEATURES = 5000
SAFE_NAME = re.compile(r"^[A-Za-z0-9_:.\-]+$")


def parse_bbox(bbox: str) -> List[float]:
    try:
        min_lon, min_lat, max_lon, max_lat = [float(v) for v in bbox.split(",")]
    except ValueError:
        raise HTTPException(status_code=422, detail="bbox must be minLon,minLat,maxLon,maxLat.")
    # A wide view can run past the world's edge, which is the same as stopping at it.
    return [max(min_lon, -180.0), max(min_lat, -90.0), min(max_lon, 180.0), min(max_lat, 90.0)]


def _split(*values: Optional[str]) -> List[str]:
    parts = [p.strip() for v in values if v for p in v.split(",")]
    return list(dict.fromkeys(p for p in parts if p and p.upper() != "ALL"))


def _srid(crs: str) -> int:
    if crs not in CRS_OPTIONS:
        raise HTTPException(status_code=422, detail=f"Unsupported coordinate reference system: {crs}")
    return int(crs.split(":")[1])


def _feature_collection(rows: List[Dict[str, Any]], truncated: bool = False) -> Dict[str, Any]:
    return {"type": "FeatureCollection", "features": rows, "truncated": truncated}


async def _authorized_ulb(tenant_id: str, user: Dict, db: AsyncSession) -> Tenant:
    normalized = (tenant_id or "").strip().upper()
    if not normalized:
        raise HTTPException(status_code=422, detail="Choose a ULB / city.")
    await ensure_tenant_access(normalized, user, db)
    tenant = await db.scalar(select(Tenant).where(Tenant.tenant_id == normalized, Tenant.ulb_type != PLATFORM_ULB_TYPE))
    if not tenant:
        raise HTTPException(status_code=404, detail="ULB / city not found.")
    return tenant


def _validate_layer(payload: GisLayerPayload) -> None:
    _srid(payload.crs)
    for value, allowed, label in (
        (payload.layerCategory, LAYER_CATEGORIES, "layer category"),
        (payload.layerType, LAYER_TYPES, "layer type"),
        (payload.dataSource, DATA_SOURCES, "data source"),
        (payload.layerStatus, LAYER_STATUSES, "layer status"),
    ):
        if value not in allowed:
            raise HTTPException(status_code=422, detail=f"Unsupported {label}: {value}")
    if payload.dataSource not in REMOTE_SOURCES:
        return
    if payload.serviceUrl and ("@" in urlparse(payload.serviceUrl).netloc):
        raise HTTPException(status_code=422, detail="GIS Service URL cannot contain a username or password.")
    if not (payload.serviceUrl and payload.layerIdentifier):
        raise HTTPException(status_code=422, detail="WMS and WFS layers need a GIS Service URL and Layer Identifier.")
    parsed = urlparse(payload.serviceUrl)
    allowed_schemes = {"https", "http"} if settings.is_development else {"https"}
    if parsed.scheme not in allowed_schemes or not parsed.netloc:
        raise HTTPException(status_code=422, detail="GIS Service URL must be a valid https address.")
    if not SAFE_NAME.match(payload.layerIdentifier):
        raise HTTPException(status_code=422, detail="Layer Identifier contains unsupported characters.")


async def approved_service_urls(db: AsyncSession, tenant_ids: List[str]) -> Dict[str, List[str]]:
    rows = (await db.execute(select(GisApprovedService.tenant_id, GisApprovedService.base_url).where(
        GisApprovedService.tenant_id.in_(tenant_ids), GisApprovedService.is_active.is_(True),
    ))).all() if tenant_ids else []
    urls: Dict[str, List[str]] = {}
    for tenant_id, url in rows:
        urls.setdefault(tenant_id, []).append(url)
    return urls


def url_is_approved(url: Optional[str], approved: List[str]) -> bool:
    """Compares whole origins and path segments, so https://gis.example.org.evil.test cannot pass."""
    if not url:
        return False
    target = urlparse(url)
    for base in approved:
        allowed = urlparse(base)
        path = allowed.path.rstrip("/")
        if (target.scheme, target.netloc) == (allowed.scheme, allowed.netloc) and (target.path == path or target.path.startswith(path + "/") or not path):
            return True
    return False


async def _require_approved_service(db: AsyncSession, tenant_id: str, payload: GisLayerPayload) -> None:
    if payload.dataSource not in REMOTE_SOURCES:
        return
    urls = await approved_service_urls(db, [tenant_id])
    if not url_is_approved(payload.serviceUrl, urls.get(tenant_id, [])):
        raise HTTPException(status_code=422, detail="This GIS Service URL is not on this ULB's approved services list.")


def _layer_response(layer: GisLayerModel, tenant_name: str, feature_count: int, approved: Optional[List[str]] = None) -> GisLayerResponse:
    remote = layer.data_source in REMOTE_SOURCES
    service_ok = not remote or approved is None or url_is_approved(layer.service_url, approved)
    return GisLayerResponse(
        serviceApproved=service_ok,
        id=layer.id,
        tenantId=layer.tenant_id,
        tenantName=tenant_name,
        stateCode=layer.state_code,
        layerName=layer.layer_name,
        layerCode=layer.layer_code,
        layerCategory=layer.layer_category,
        layerType=layer.layer_type,
        dataSource=layer.data_source,
        # A service that lost its approval must not reach a viewer's browser.
        serviceUrl=layer.service_url if service_ok else None,
        workspaceName=layer.workspace_name,
        layerIdentifier=layer.layer_identifier,
        crs=layer.crs,
        defaultVisibility=layer.default_visibility,
        opacity=layer.opacity,
        layerStyle=layer.layer_style or {},
        layerStatus=layer.layer_status,
        utilityCategory=layer.utility_category,
        networkType=layer.network_type,
        department=layer.department,
        featureCount=feature_count,
        lastSyncedAt=layer.last_synced_at,
    )


@router.get("/options", response_model=ApiResponse[GisOptions])
async def get_options(
    tenantId: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    stmt = select(Tenant).where(Tenant.ulb_type != PLATFORM_ULB_TYPE).order_by(Tenant.name)
    if not is_super_admin(user):
        stmt = stmt.where(tenant_scope_filter(user))
    tenants = (await db.scalars(stmt)).all()
    wards: List[Dict[str, str]] = []
    zones: List[Dict[str, str]] = []
    if tenantId:
        tenant = await _authorized_ulb(tenantId, user, db)
        wards = [
            {"id": w.id, "name": f"{w.ward_number} - {w.ward_name}", "zoneId": w.zone_id or ""}
            for w in (await db.scalars(select(Ward).where(Ward.tenant_id == tenant.tenant_id).order_by(Ward.ward_number))).all()
        ]
        zones = [
            {"id": z.id, "name": z.name}
            for z in (await db.scalars(select(Zone).where(Zone.tenant_id == tenant.tenant_id).order_by(Zone.name))).all()
        ]
    categories = (await db.scalars(select(distinct(PropertyUnit.usage_category)).order_by(PropertyUnit.usage_category))).all()
    statuses = (await db.scalars(select(distinct(PropertyUnit.tax_status)).order_by(PropertyUnit.tax_status))).all()
    base_maps: List[Dict[str, Any]] = [
        {"code": "osm", "name": "OpenStreetMap", "url": "https://tile.openstreetmap.org/{z}/{x}/{y}.png", "attribution": "&copy; OpenStreetMap contributors", "maxZoom": 19},
        {"code": "satellite", "name": "Satellite", "url": "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}", "attribution": "Imagery &copy; Esri", "maxZoom": 19},
        {"code": "terrain", "name": "Terrain", "url": "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", "attribution": "&copy; OpenTopoMap (CC-BY-SA), OpenStreetMap contributors", "maxZoom": 17},
    ]
    if settings.GIS_CUSTOM_BASEMAP_URL:
        base_maps.append({"code": "custom", "name": "Custom Government Basemap", "url": settings.GIS_CUSTOM_BASEMAP_URL, "attribution": settings.GIS_CUSTOM_BASEMAP_ATTRIBUTION, "maxZoom": 19})
    return ApiResponse(
        data=GisOptions(
            states=[{"code": c, "name": c} for c in sorted({t.state_code for t in tenants if t.state_code})],
            ulbs=[{"code": t.tenant_id, "name": t.name, "stateCode": t.state_code, "district": t.district or ""} for t in tenants],
            districts=sorted({t.district for t in tenants if t.district}),
            wards=wards,
            zones=zones,
            baseMaps=base_maps,
            crsOptions=[{"code": code, "name": name} for code, name in CRS_OPTIONS.items()],
            geographicScopes=GEOGRAPHIC_SCOPES,
            surveyStatuses=SURVEY_STATUSES,
            refreshIntervals=["Manual", "1 minute", "5 minutes", "15 minutes"],
            layerCategories=LAYER_CATEGORIES,
            layerTypes=LAYER_TYPES,
            dataSources=DATA_SOURCES,
            layerStatuses=LAYER_STATUSES,
            boundaryLevels=["ULB", "Zone", "Ward"],
            utilityCategories=["Water Supply", "Sewerage", "Stormwater Drainage", "Electricity", "Street Lighting", "Telecommunications"],
            utilityNetworkTypes=["Transmission", "Distribution", "Collection", "Service Connection"],
            assetStatuses=["Operational", "Under Maintenance", "Planned", "Decommissioned"],
            roadCategories=["Arterial", "Sub-Arterial", "Collector", "Local", "Service Lane"],
            roadStatuses=["Open", "Under Repair", "Closed", "Proposed"],
            roadSurfaces=["Bituminous", "Concrete", "Paver Block", "Gravel", "Earthen"],
            parcelCategories=list(categories),
            parcelStatuses=list(statuses),
        )
    )


@router.get("/scope", response_model=PagedResponse[GisScopeRow])
async def get_scope(
    stateTenants: Optional[str] = Query(None),
    districts: Optional[str] = Query(None),
    ulbTenants: Optional[str] = Query(None),
    boundaryStatus: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = [Tenant.ulb_type != PLATFORM_ULB_TYPE]
    if not is_super_admin(user):
        conditions.append(tenant_scope_filter(user))
    states, ulbs, wanted = _split(stateTenants), _split(ulbTenants), _split(districts)
    if states:
        conditions.append(func.upper(Tenant.state_code).in_([s.upper() for s in states]))
    if ulbs:
        conditions.append(func.upper(Tenant.tenant_id).in_([u.upper() for u in ulbs]))
    if wanted:
        conditions.append(Tenant.district.in_(wanted))
    if boundaryStatus and boundaryStatus != "ALL":
        conditions.append(Tenant.status == boundaryStatus)
    if search and search.strip():
        conditions.append(or_(Tenant.name.ilike(f"%{search.strip()}%"), Tenant.tenant_id.ilike(f"%{search.strip()}%")))
    total = await db.scalar(select(func.count(Tenant.tenant_id)).where(*conditions)) or 0
    tenants = (await db.scalars(select(Tenant).where(*conditions).order_by(Tenant.name).offset(skip).limit(limit))).all()
    ids = [t.tenant_id for t in tenants]

    async def by_tenant(column, *extra):
        return dict((await db.execute(select(column, func.count()).where(column.in_(ids), *extra).group_by(column))).all()) if ids else {}

    wards = await by_tenant(Ward.tenant_id)
    mapped = await by_tenant(Ward.tenant_id, Ward.geom.isnot(None))
    parcels = await by_tenant(PropertyParcel.tenant_id)
    layers = await by_tenant(GisLayerModel.tenant_id)
    synced = dict((await db.execute(select(GisLayerModel.tenant_id, func.max(GisLayerModel.last_synced_at)).where(GisLayerModel.tenant_id.in_(ids)).group_by(GisLayerModel.tenant_id))).all()) if ids else {}
    return PagedResponse(total=total, data=[
        GisScopeRow(
            tenantId=t.tenant_id, tenantName=t.name, stateCode=t.state_code, district=t.district or "", status=t.status or "",
            wardCount=wards.get(t.tenant_id, 0), wardBoundaryCount=mapped.get(t.tenant_id, 0), parcelCount=parcels.get(t.tenant_id, 0),
            layerCount=layers.get(t.tenant_id, 0), lastSyncedAt=synced.get(t.tenant_id),
        )
        for t in tenants
    ])


@router.get("/boundaries")
async def get_boundaries(
    tenantId: str = Query(...),
    level: str = Query("Ward"),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    tenant = await _authorized_ulb(tenantId, user, db)
    if level == "Ward":
        statement = "SELECT ward_name AS name, ward_number AS code, ST_AsGeoJSON(geom)::json AS geometry FROM wards WHERE tenant_id = :tenant AND geom IS NOT NULL"
    elif level == "Zone":
        statement = "SELECT name, code, ST_AsGeoJSON(geom)::json AS geometry FROM zones WHERE tenant_id = :tenant AND geom IS NOT NULL"
    elif level == "ULB":
        # A city's outline is the union of its wards.
        statement = f"SELECT :name AS name, :tenant AS code, ST_AsGeoJSON({ULB_REGION_SQL})::json AS geometry WHERE {ULB_REGION_SQL} IS NOT NULL"
    else:
        raise HTTPException(status_code=422, detail="Boundary level must be ULB, Zone or Ward.")
    params = {"tenant": tenant.tenant_id, **({"name": tenant.name} if level == "ULB" else {})}
    rows = (await db.execute(text(statement), params)).mappings().all()
    return _feature_collection([
        {"type": "Feature", "geometry": r["geometry"], "properties": {"name": r["name"], "code": str(r["code"]), "level": level, "tenantId": tenant.tenant_id}}
        for r in rows
    ])


# Layers


@router.get("/layers", response_model=PagedResponse[GisLayerResponse])
async def list_layers(
    tenantId: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    utilityCategory: Optional[str] = Query(None),
    layerStatus: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    conditions = []
    if tenantId:
        conditions.append(GisLayerModel.tenant_id == (await _authorized_ulb(tenantId, user, db)).tenant_id)
    elif not is_super_admin(user):
        conditions.append(tenant_scope_filter(user))
    if category:
        conditions.append(GisLayerModel.layer_category.in_(_split(category)))
    if utilityCategory:
        conditions.append(GisLayerModel.utility_category.in_(_split(utilityCategory)))
    if layerStatus:
        conditions.append(GisLayerModel.layer_status == layerStatus)
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(GisLayerModel.layer_name.ilike(term), GisLayerModel.layer_code.ilike(term)))
    base = select(GisLayerModel, Tenant.name).join(Tenant, Tenant.tenant_id == GisLayerModel.tenant_id).where(*conditions)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = (await db.execute(base.order_by(GisLayerModel.layer_name).offset(skip).limit(limit))).all()
    counts = dict((await db.execute(
        select(GisFeatureModel.layer_id, func.count(GisFeatureModel.id))
        .where(GisFeatureModel.layer_id.in_([l.id for l, _ in rows]))
        .group_by(GisFeatureModel.layer_id)
    )).all()) if rows else {}
    approved = await approved_service_urls(db, list({l.tenant_id for l, _ in rows}))
    return PagedResponse(total=total, data=[_layer_response(l, name, counts.get(l.id, 0), approved.get(l.tenant_id, [])) for l, name in rows])


async def _apply_layer(layer: GisLayerModel, payload: GisLayerPayload) -> None:
    layer.layer_name = payload.layerName.strip()
    layer.layer_code = payload.layerCode.strip().upper()
    layer.layer_category = payload.layerCategory
    layer.layer_type = payload.layerType
    layer.data_source = payload.dataSource
    remote = payload.dataSource in REMOTE_SOURCES
    layer.service_url = payload.serviceUrl if remote else None
    layer.workspace_name = payload.workspaceName if remote else None
    layer.layer_identifier = payload.layerIdentifier if remote else None
    layer.crs = payload.crs
    layer.default_visibility = payload.defaultVisibility
    layer.opacity = payload.opacity
    layer.layer_style = payload.layerStyle
    layer.layer_status = payload.layerStatus
    layer.utility_category = payload.utilityCategory
    layer.network_type = payload.networkType
    layer.department = payload.department


@router.post("/layers", response_model=ApiResponse[GisLayerResponse], status_code=status.HTTP_201_CREATED)
async def create_layer(payload: GisLayerPayload, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    tenant = await _authorized_ulb(payload.tenantId, user, db)
    _validate_layer(payload)
    await _require_approved_service(db, tenant.tenant_id, payload)
    code = payload.layerCode.strip().upper()
    if await db.scalar(select(GisLayerModel.id).where(GisLayerModel.tenant_id == tenant.tenant_id, GisLayerModel.layer_code == code)):
        raise HTTPException(status_code=400, detail=f"Layer code '{code}' already exists for this ULB.")
    layer = GisLayerModel(tenant_id=tenant.tenant_id, state_code=tenant.state_code)
    await _apply_layer(layer, payload)
    db.add(layer)
    add_audit(db, tenant.tenant_id, "GIS_LAYER_CREATED", user, f"Layer {code} created.")
    await db.commit()
    await db.refresh(layer)
    return ApiResponse(data=_layer_response(layer, tenant.name, 0))


async def _authorized_layer(layer_id: str, user: Dict, db: AsyncSession) -> GisLayerModel:
    layer = await db.scalar(select(GisLayerModel).where(GisLayerModel.id == layer_id))
    if not layer:
        raise HTTPException(status_code=404, detail="Layer not found.")
    await ensure_tenant_access(layer.tenant_id, user, db)
    return layer


@router.put("/layers/{layer_id}", response_model=ApiResponse[GisLayerResponse])
async def update_layer(layer_id: str, payload: GisLayerPayload, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    layer = await _authorized_layer(layer_id, user, db)
    if payload.tenantId.strip().upper() != layer.tenant_id:
        raise HTTPException(status_code=422, detail="A layer cannot be moved to another ULB.")
    _validate_layer(payload)
    await _require_approved_service(db, layer.tenant_id, payload)
    await _apply_layer(layer, payload)
    add_audit(db, layer.tenant_id, "GIS_LAYER_UPDATED", user, f"Layer {layer.layer_code} updated.")
    await db.commit()
    await db.refresh(layer)
    tenant = await db.scalar(select(Tenant).where(Tenant.tenant_id == layer.tenant_id))
    count = await db.scalar(select(func.count(GisFeatureModel.id)).where(GisFeatureModel.layer_id == layer.id)) or 0
    return ApiResponse(data=_layer_response(layer, tenant.name if tenant else "", count))


@router.delete("/layers/{layer_id}", response_model=ApiResponse[dict])
async def delete_layer(layer_id: str, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    layer = await _authorized_layer(layer_id, user, db)
    add_audit(db, layer.tenant_id, "GIS_LAYER_DELETED", user, f"Layer {layer.layer_code} deleted.")
    await db.delete(layer)
    await db.commit()
    return ApiResponse(data={"id": layer_id})


def declared_crs(collection: Dict[str, Any]) -> Optional[str]:
    """The CRS a GeoJSON file names, in EPSG:n form. RFC 7946 files name none and are longitude and latitude."""
    name = ((collection.get("crs") or {}).get("properties") or {}).get("name")
    if not isinstance(name, str):
        return None
    if name.upper().endswith("CRS84"):
        return "EPSG:4326"
    match = re.search(r"EPSG:+(\d+)$", name.upper())
    return f"EPSG:{match.group(1)}" if match else name


async def replace_features(db: AsyncSession, layer: GisLayerModel, features: List[Any], srid: int, clip: bool = False) -> GisImportResult:
    """Stores new features, then removes the old ones. If none are usable the layer keeps what it has."""
    region_check = f"AND ST_Intersects(g, {ULB_REGION_SQL})" if clip else ""
    geometry_sql = f"ST_Multi(ST_CollectionExtract(ST_Intersection(g, {ULB_REGION_SQL}), {_extract_type(layer.layer_type)}))" if clip else "g"
    allowed = GEOMETRY_TYPES.get(layer.layer_type)
    type_check = f"AND GeometryType(g) IN ({allowed})" if allowed else ""
    insert = text(
        "WITH s AS (SELECT ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(CAST(:geometry AS text)), CAST(:srid AS integer)), 4326) AS g) "
        "INSERT INTO gis_features (id, layer_id, tenant_id, feature_ref, properties, geom, created_at) "
        f"SELECT CAST(:id AS varchar), CAST(:layer AS varchar), CAST(:tenant AS varchar), CAST(:ref AS varchar), CAST(:props AS json), {geometry_sql}, now() "
        f"FROM s WHERE ST_IsValid(g) AND ST_XMin(g) >= -180 AND ST_XMax(g) <= 180 AND ST_YMin(g) >= -90 AND ST_YMax(g) <= 90 {type_check} {region_check}"
    )
    new_ids: List[str] = []
    rejected = 0
    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not geometry:
            rejected += 1
            continue
        properties = feature.get("properties") or {}
        feature_id = str(uuid.uuid4())
        try:
            async with db.begin_nested():
                result = await db.execute(insert, {
                    "id": feature_id, "layer": layer.id, "tenant": layer.tenant_id,
                    "ref": str(feature.get("id") or properties.get("id") or "")[:100] or None,
                    "props": json.dumps(properties), "srid": srid, "geometry": json.dumps(geometry),
                })
            if result.rowcount:
                new_ids.append(feature_id)
            else:
                rejected += 1
        except Exception:
            rejected += 1
    if not new_ids:
        await db.rollback()
        raise HTTPException(status_code=422, detail=f"None of the {len(features)} features could be used, so the layer was left unchanged. Check the CRS and geometry type.")
    await db.execute(text("DELETE FROM gis_features WHERE layer_id = :layer AND id <> ALL(CAST(:ids AS varchar[]))"), {"layer": layer.id, "ids": new_ids})
    layer.last_synced_at = datetime.datetime.utcnow()
    return GisImportResult(imported=len(new_ids), rejected=rejected)


def _extract_type(layer_type: str) -> int:
    return {"Point": 1, "Line": 2, "Polygon": 3}.get(layer_type, 3)


def features_of(collection: Dict[str, Any]) -> List[Any]:
    features = collection.get("features") if collection.get("type") == "FeatureCollection" else None
    if not isinstance(features, list):
        raise HTTPException(status_code=422, detail="Upload a GeoJSON FeatureCollection.")
    if len(features) > MAX_IMPORT_FEATURES:
        raise HTTPException(status_code=422, detail=f"Import at most {MAX_IMPORT_FEATURES} features at a time.")
    return features


@router.post("/layers/{layer_id}/features", response_model=ApiResponse[GisImportResult])
async def import_features(layer_id: str, payload: GisImportPayload, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    """Replaces a stored layer's features from GeoJSON, transforming them to EPSG:4326."""
    layer = await _authorized_layer(layer_id, user, db)
    if layer.data_source in REMOTE_SOURCES:
        raise HTTPException(status_code=409, detail="WMS and WFS layers are read from their service.")
    if layer.layer_type == "Raster":
        raise HTTPException(status_code=409, detail="Raster layers do not store features.")
    srid = _srid(payload.sourceCrs)
    if payload.sourceCrs != layer.crs:
        raise HTTPException(status_code=422, detail=f"This layer is declared as {layer.crs}. Change the layer's CRS, or import data in that CRS.")
    named = declared_crs(payload.featureCollection)
    if named and named != payload.sourceCrs:
        raise HTTPException(status_code=422, detail=f"This file says it is in {named}, but {payload.sourceCrs} was selected.")
    result = await replace_features(db, layer, features_of(payload.featureCollection), srid)
    add_audit(db, layer.tenant_id, "GIS_FEATURES_IMPORTED", user, f"{result.imported} features imported into {layer.layer_code}, {result.rejected} rejected.")
    await db.commit()
    return ApiResponse(data=result)


# Features. Map responses are GeoJSON, capped rather than paged.


@router.get("/features")
async def query_features(
    tenantId: str = Query(...),
    layerIds: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    bbox: Optional[str] = Query(None, description="minLon,minLat,maxLon,maxLat in EPSG:4326"),
    outputCrs: str = Query("EPSG:4326"),
    assetStatus: Optional[str] = Query(None),
    roadCategory: Optional[str] = Query(None),
    roadStatus: Optional[str] = Query(None),
    roadSurface: Optional[str] = Query(None),
    zone: Optional[str] = Query(None),
    ward: Optional[str] = Query(None),
    minWidth: Optional[float] = Query(None),
    maxWidth: Optional[float] = Query(None),
    dataSource: Optional[str] = Query(None),
    utilityCategory: Optional[str] = Query(None),
    networkType: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=MAX_FEATURES),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    tenant = await _authorized_ulb(tenantId, user, db)
    output_srid = _srid(outputCrs)
    clauses = ["f.tenant_id = :tenant", "l.tenant_id = :tenant", "l.layer_status = 'Active'"]
    params: Dict[str, Any] = {"tenant": tenant.tenant_id, "srid": output_srid, "limit": limit + 1}

    def any_of(column: str, values: List[str], name: str) -> None:
        names = []
        for index, value in enumerate(values):
            key = f"{name}{index}"
            params[key] = value
            names.append(f":{key}")
        clauses.append(f"{column} IN ({', '.join(names)})")

    if layerIds:
        any_of("l.id", _split(layerIds), "layer")
    if category:
        any_of("l.layer_category", _split(category), "category")
    if dataSource:
        any_of("l.data_source", _split(dataSource), "source")
    if utilityCategory:
        any_of("l.utility_category", _split(utilityCategory), "utility")
    if networkType:
        any_of("l.network_type", _split(networkType), "network")
    if department and department.strip():
        clauses.append("l.department ILIKE :department")
        params["department"] = f"%{department.strip()}%"
    for value, field, name in (
        (assetStatus, "assetStatus", "asset"),
        (roadCategory, "roadCategory", "road"),
        (roadStatus, "roadStatus", "state"),
        (roadSurface, "surface", "surface"),
    ):
        if value:
            any_of(f"f.properties->>'{field}'", _split(value), name)

    def named_keys(values: List[str], name: str) -> str:
        keys = []
        for index, value in enumerate(values):
            params[f"{name}{index}"] = value
            keys.append(f":{name}{index}")
        return ", ".join(keys)

    # Spatial where boundaries exist. Features tagged with the name still match where they do not.
    if zone:
        keys = named_keys(_split(zone), "zone")
        clauses.append(
            "(COALESCE(ST_Intersects(f.geom, (SELECT ST_Union(g) FROM ("
            f"SELECT z.geom AS g FROM zones z WHERE z.tenant_id = :tenant AND z.name IN ({keys}) "
            f"UNION ALL SELECT w.geom FROM wards w JOIN zones z ON z.id = w.zone_id WHERE w.tenant_id = :tenant AND z.name IN ({keys})) u)), false) "
            f"OR f.properties->>'zone' IN ({keys}))"
        )
    if ward:
        keys = named_keys(_split(ward), "ward")
        clauses.append(
            f"(COALESCE(ST_Intersects(f.geom, (SELECT ST_Union(w.geom) FROM wards w WHERE w.tenant_id = :tenant AND (w.ward_name IN ({keys}) OR w.id IN ({keys})))), false) "
            f"OR f.properties->>'ward' IN ({keys}))"
        )
    if minWidth is not None:
        clauses.append(f"{WIDTH_SQL} >= :min_width")
        params["min_width"] = minWidth
    if maxWidth is not None:
        clauses.append(f"{WIDTH_SQL} <= :max_width")
        params["max_width"] = maxWidth
    if bbox:
        min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)
        clauses.append("ST_Intersects(f.geom, ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326))")
        params.update(min_lon=min_lon, min_lat=min_lat, max_lon=max_lon, max_lat=max_lat)
    rows = (await db.execute(
        text(
            "SELECT f.id, f.feature_ref, f.properties, l.id AS layer_id, l.layer_name, l.layer_category, l.layer_style, "
            "ST_AsGeoJSON(ST_Transform(f.geom, CAST(:srid AS integer)))::json AS geometry "
            "FROM gis_features f JOIN gis_layers l ON l.id = f.layer_id "
            f"WHERE {' AND '.join(clauses)} ORDER BY f.id LIMIT :limit"
        ),
        params,
    )).mappings().all()
    return _feature_collection(
        [
            {
                "type": "Feature",
                "id": r["id"],
                "geometry": r["geometry"],
                "properties": {**(r["properties"] or {}), "_ref": r["feature_ref"], "_layerId": r["layer_id"], "_layer": r["layer_name"], "_category": r["layer_category"], "_style": r["layer_style"] or {}},
            }
            for r in rows[:limit]
        ],
        truncated=len(rows) > limit,
    ) | {"crs": outputCrs}


async def resolve_scope(scope: str, states: List[str], ulbs: List[str], extent: Optional[List[float]], user: Dict, db: AsyncSession) -> List[Tenant]:
    """The ULBs a Geographic Scope means for this user. Asking for anything outside their access is refused, never widened."""
    if scope not in GEOGRAPHIC_SCOPES:
        raise HTTPException(status_code=422, detail=f"Unsupported geographic scope: {scope}")
    if scope == "Selected States" and not states:
        raise HTTPException(status_code=422, detail="Choose at least one state for this geographic scope.")
    if scope == "Selected ULBs" and not ulbs:
        raise HTTPException(status_code=422, detail="Choose at least one ULB / city for this geographic scope.")
    if scope == "Custom Extent" and not extent:
        raise HTTPException(status_code=422, detail="Set a map extent for this geographic scope.")
    conditions: List[Any] = [Tenant.ulb_type != PLATFORM_ULB_TYPE]
    if not is_super_admin(user):
        conditions.append(tenant_scope_filter(user))
    accessible = (await db.scalars(select(Tenant).where(*conditions).order_by(Tenant.name))).all()
    wanted_states = {s.upper() for s in states}
    wanted_ulbs = {u.upper() for u in ulbs}
    known_states = {(t.state_code or "").upper() for t in accessible}
    known_ulbs = {t.tenant_id.upper() for t in accessible}
    if wanted_states - known_states or wanted_ulbs - known_ulbs:
        raise HTTPException(status_code=403, detail="You do not have access to part of this geographic scope.")
    return [
        t for t in accessible
        if (not wanted_states or (t.state_code or "").upper() in wanted_states) and (not wanted_ulbs or t.tenant_id.upper() in wanted_ulbs)
    ]


@router.get("/features/scope")
async def query_scope_features(
    geographicScope: str = Query(...),
    stateTenants: Optional[str] = Query(None),
    ulbTenants: Optional[str] = Query(None),
    extent: Optional[str] = Query(None, description="west,south,east,north"),
    layerIds: Optional[str] = Query(None),
    includeParcels: bool = Query(False),
    bbox: Optional[str] = Query(None),
    outputCrs: str = Query("EPSG:4326"),
    limit: int = Query(1000, ge=1, le=MAX_FEATURES),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    """Features across every ULB a scope covers, for the Map Overview and exports."""
    output_srid = _srid(outputCrs)
    extent_box = parse_bbox(extent) if extent else None
    tenants = await resolve_scope(geographicScope, _split(stateTenants), _split(ulbTenants), extent_box, user, db)
    ids = [t.tenant_id for t in tenants]
    if not ids:
        return _feature_collection([]) | {"crs": outputCrs, "tenantCount": 0}
    boxes = [parse_bbox(b) for b in (extent, bbox) if b]
    params: Dict[str, Any] = {"ids": ids, "srid": output_srid, "limit": limit + 1}
    clauses = ["f.tenant_id = ANY(CAST(:ids AS varchar[]))", "l.tenant_id = f.tenant_id", "l.layer_status = 'Active'"]
    for index, box in enumerate(boxes):
        clauses.append(f"ST_Intersects(f.geom, ST_MakeEnvelope(:w{index}, :s{index}, :e{index}, :n{index}, 4326))")
        params.update({f"w{index}": box[0], f"s{index}": box[1], f"e{index}": box[2], f"n{index}": box[3]})
    wanted_layers = _split(layerIds)
    if wanted_layers:
        clauses.append("l.id = ANY(CAST(:layers AS varchar[]))")
        params["layers"] = wanted_layers
    rows = (await db.execute(text(
        "SELECT f.id, f.feature_ref, f.properties, f.tenant_id, l.id AS layer_id, l.layer_name, l.layer_category, l.layer_style, "
        "ST_AsGeoJSON(ST_Transform(f.geom, CAST(:srid AS integer)))::json AS geometry "
        f"FROM gis_features f JOIN gis_layers l ON l.id = f.layer_id WHERE {' AND '.join(clauses)} ORDER BY f.id LIMIT :limit"
    ), params)).mappings().all()
    features = [
        {"type": "Feature", "id": r["id"], "geometry": r["geometry"],
         "properties": {**(r["properties"] or {}), "_ref": r["feature_ref"], "_tenant": r["tenant_id"], "_layerId": r["layer_id"], "_layer": r["layer_name"], "_category": r["layer_category"], "_style": r["layer_style"] or {}}}
        for r in rows[:limit]
    ]
    truncated = len(rows) > limit
    if includeParcels and len(features) < limit:
        room = limit - len(features)
        conditions: List[Any] = [PropertyParcel.tenant_id.in_(ids), PropertyParcel.geom.isnot(None)]
        for box in boxes:
            conditions.append(func.ST_Intersects(PropertyParcel.geom, func.ST_MakeEnvelope(*box, 4326)))
        shape = func.ST_Transform(func.coalesce(PropertyParcel.boundary_geom, PropertyParcel.geom), output_srid)
        parcels = (await db.execute(
            select(PropertyParcel.id, PropertyParcel.ulpin, PropertyParcel.tenant_id, func.ST_AsGeoJSON(shape))
            .where(*conditions).order_by(PropertyParcel.ulpin).limit(room + 1)
        )).all()
        truncated = truncated or len(parcels) > room
        features += [
            {"type": "Feature", "id": pid, "geometry": json.loads(geometry), "properties": {"ulpin": ulpin, "_tenant": tenant_id, "_layer": "Registered Parcels", "_category": "Parcel"}}
            for pid, ulpin, tenant_id, geometry in parcels[:room]
        ]
    return _feature_collection(features, truncated=truncated) | {"crs": outputCrs, "tenantCount": len(ids)}


@router.get("/transform")
async def transform_point(lon: float = Query(..., ge=-180, le=180), lat: float = Query(..., ge=-90, le=90), crs: str = Query(...), db: AsyncSession = Depends(get_read_db)):
    row = (await db.execute(
        text("SELECT ST_X(p) AS x, ST_Y(p) AS y FROM (SELECT ST_Transform(ST_SetSRID(ST_MakePoint(:lon, :lat), 4326), CAST(:srid AS integer)) AS p) s"),
        {"lon": lon, "lat": lat, "srid": _srid(crs)},
    )).mappings().one()
    return {"x": row["x"], "y": row["y"], "crs": crs}


def _bbox_filter(column, bbox: Optional[str]) -> List[Any]:
    if not bbox:
        return []
    return [func.ST_Intersects(column, func.ST_MakeEnvelope(*parse_bbox(bbox), 4326))]


@router.get("/parcels")
async def query_parcels(
    tenantId: str = Query(...),
    wards: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    statuses: Optional[str] = Query(None),
    surveyStatus: Optional[str] = Query(None),
    gisStatus: Optional[str] = Query(None, description="mapped or unmapped"),
    search: Optional[str] = Query(None),
    bbox: Optional[str] = Query(None),
    boundaryDisplay: bool = Query(True),
    limit: int = Query(1000, ge=1, le=MAX_FEATURES),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    """Parcels are drawn as their surveyed boundary where one exists, otherwise as a point."""
    tenant = await _authorized_ulb(tenantId, user, db)
    conditions: List[Any] = [PropertyParcel.tenant_id == tenant.tenant_id]
    if gisStatus == "unmapped":
        return _feature_collection([]) | {"unmapped": await db.scalar(select(func.count(PropertyParcel.id)).where(*conditions, PropertyParcel.geom.is_(None))) or 0}
    conditions.append(PropertyParcel.geom.isnot(None))
    if wards:
        conditions.append(PropertyParcel.ward_id.in_(_split(wards)))
    if surveyStatus:
        conditions.append(PropertyParcel.survey_status == surveyStatus)
    unit_filters = []
    if categories:
        unit_filters.append(PropertyUnit.usage_category.in_(_split(categories)))
    if statuses:
        unit_filters.append(PropertyUnit.tax_status.in_(_split(statuses)))
    if unit_filters:
        conditions.append(
            select(PropertyUnit.id).join(Building, PropertyUnit.building_id == Building.id)
            .where(Building.parcel_id == PropertyParcel.id, *unit_filters).exists()
        )
    if search and search.strip():
        term = f"%{search.strip()}%"
        conditions.append(or_(PropertyParcel.ulpin.ilike(term), PropertyParcel.survey_number.ilike(term)))
    conditions += _bbox_filter(PropertyParcel.geom, bbox)
    shape = func.coalesce(PropertyParcel.boundary_geom, PropertyParcel.geom) if boundaryDisplay else PropertyParcel.geom
    rows = (await db.execute(
        select(PropertyParcel, Ward.ward_name, func.ST_AsGeoJSON(shape))
        .outerjoin(Ward, Ward.id == PropertyParcel.ward_id).where(*conditions).order_by(PropertyParcel.ulpin).limit(limit + 1)
    )).all()
    return _feature_collection(
        [
            {
                "type": "Feature",
                "id": p.id,
                "geometry": json.loads(geometry),
                "properties": {"ulpin": p.ulpin, "surveyNumber": p.survey_number, "address": p.address, "ward": ward_name, "surveyStatus": p.survey_status, "_layer": "Registered Parcels", "_category": "Parcel"},
            }
            for p, ward_name, geometry in rows[:limit]
        ],
        truncated=len(rows) > limit,
    )


# Workspaces belong to the person who saved them.


def _workspace_owner(user: Dict) -> str:
    return str(user.get("email") or user.get("preferred_username") or user.get("sub") or "")


def _workspace_response(w: GisWorkspaceModel) -> GisWorkspaceResponse:
    return GisWorkspaceResponse(
        id=w.id, workspaceName=w.workspace_name, geographicScope=w.geographic_scope, stateTenants=w.state_tenants or [],
        ulbTenants=w.ulb_tenants or [], mapExtent=w.map_extent, baseMap=w.base_map, crs=w.crs, defaultZoom=w.default_zoom,
        defaultCentre=w.default_centre, visibleLayers=w.visible_layers or [], refreshInterval=w.refresh_interval, updatedAt=w.updated_at,
    )


@router.get("/workspaces", response_model=ApiResponse[List[GisWorkspaceResponse]])
async def list_workspaces(
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    stmt = select(GisWorkspaceModel).where(GisWorkspaceModel.owner == _workspace_owner(user)).order_by(GisWorkspaceModel.updated_at.desc())
    if search and search.strip():
        stmt = stmt.where(GisWorkspaceModel.workspace_name.ilike(f"%{search.strip()}%"))
    return ApiResponse(data=[_workspace_response(w) for w in (await db.scalars(stmt.offset(skip).limit(limit))).all()])


async def _apply_workspace(workspace: GisWorkspaceModel, payload: GisWorkspacePayload, user: Dict, db: AsyncSession) -> None:
    _srid(payload.crs)
    # A saved view cannot widen access, because the same checks run when it is used.
    await resolve_scope(payload.geographicScope, payload.stateTenants, payload.ulbTenants, payload.mapExtent, user, db)
    workspace.workspace_name = payload.workspaceName or "Untitled workspace"
    workspace.geographic_scope = payload.geographicScope
    workspace.state_tenants = payload.stateTenants
    workspace.ulb_tenants = payload.ulbTenants
    workspace.map_extent = payload.mapExtent
    workspace.base_map = payload.baseMap
    workspace.crs = payload.crs
    workspace.default_zoom = payload.defaultZoom
    workspace.default_centre = payload.defaultCentre
    workspace.visible_layers = payload.visibleLayers
    workspace.refresh_interval = payload.refreshInterval


async def _owned_workspace(workspace_id: str, user: Dict, db: AsyncSession) -> GisWorkspaceModel:
    workspace = await db.scalar(select(GisWorkspaceModel).where(GisWorkspaceModel.id == workspace_id, GisWorkspaceModel.owner == _workspace_owner(user)))
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    return workspace


@router.put("/workspaces/{workspace_id}", response_model=ApiResponse[GisWorkspaceResponse])
async def update_workspace(workspace_id: str, payload: GisWorkspacePayload, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_write_db)):
    workspace = await _owned_workspace(workspace_id, user, db)
    await _apply_workspace(workspace, payload, user, db)
    await db.commit()
    await db.refresh(workspace)
    return ApiResponse(data=_workspace_response(workspace))


@router.delete("/workspaces/{workspace_id}", response_model=ApiResponse[dict])
async def delete_workspace(workspace_id: str, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_write_db)):
    workspace = await _owned_workspace(workspace_id, user, db)
    await db.delete(workspace)
    await db.commit()
    return ApiResponse(data={"id": workspace_id})


@router.post("/workspaces", response_model=ApiResponse[GisWorkspaceResponse], status_code=status.HTTP_201_CREATED)
async def save_workspace(payload: GisWorkspacePayload, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_write_db)):
    workspace = GisWorkspaceModel(owner=_workspace_owner(user))
    await _apply_workspace(workspace, payload, user, db)
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return ApiResponse(data=_workspace_response(workspace))
