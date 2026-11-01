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

from app.core.auth import ensure_tenant_access, get_current_user, is_super_admin, require_roles, tenant_scope_filter
from app.core.config import PLATFORM_ULB_TYPE, settings
from app.db.models import (
    Building,
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
MAX_FEATURES = 5000
MAX_IMPORT_FEATURES = 5000
SAFE_NAME = re.compile(r"^[A-Za-z0-9_:.\-]+$")


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
    if not (payload.serviceUrl and payload.layerIdentifier):
        raise HTTPException(status_code=422, detail="WMS and WFS layers need a GIS Service URL and Layer Identifier.")
    parsed = urlparse(payload.serviceUrl)
    allowed_schemes = {"https", "http"} if settings.is_development else {"https"}
    if parsed.scheme not in allowed_schemes or not parsed.netloc:
        raise HTTPException(status_code=422, detail="GIS Service URL must be a valid https address.")
    if not SAFE_NAME.match(payload.layerIdentifier):
        raise HTTPException(status_code=422, detail="Layer Identifier contains unsupported characters.")


def _layer_response(layer: GisLayerModel, tenant_name: str, feature_count: int) -> GisLayerResponse:
    return GisLayerResponse(
        id=layer.id,
        tenantId=layer.tenant_id,
        tenantName=tenant_name,
        stateCode=layer.state_code,
        layerName=layer.layer_name,
        layerCode=layer.layer_code,
        layerCategory=layer.layer_category,
        layerType=layer.layer_type,
        dataSource=layer.data_source,
        serviceUrl=layer.service_url,
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
        base_maps.append({"code": "custom", "name": "Custom Government Basemap", "url": settings.GIS_CUSTOM_BASEMAP_URL, "attribution": "Government of India", "maxZoom": 19})
    return ApiResponse(
        data=GisOptions(
            states=[{"code": c, "name": c} for c in sorted({t.state_code for t in tenants if t.state_code})],
            ulbs=[{"code": t.tenant_id, "name": t.name, "stateCode": t.state_code, "district": t.district or ""} for t in tenants],
            districts=sorted({t.district for t in tenants if t.district}),
            wards=wards,
            zones=zones,
            baseMaps=base_maps,
            crsOptions=[{"code": code, "name": name} for code, name in CRS_OPTIONS.items()],
            geographicScopes=["All Accessible States", "Selected States", "Selected ULBs", "Custom Extent"],
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


@router.get("/scope", response_model=ApiResponse[List[GisScopeRow]])
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
    stmt = select(Tenant).where(Tenant.ulb_type != PLATFORM_ULB_TYPE).order_by(Tenant.name)
    if not is_super_admin(user):
        stmt = stmt.where(tenant_scope_filter(user))
    states, ulbs, wanted = _split(stateTenants), _split(ulbTenants), _split(districts)
    if states:
        stmt = stmt.where(func.upper(Tenant.state_code).in_([s.upper() for s in states]))
    if ulbs:
        stmt = stmt.where(func.upper(Tenant.tenant_id).in_([u.upper() for u in ulbs]))
    if wanted:
        stmt = stmt.where(Tenant.district.in_(wanted))
    if boundaryStatus and boundaryStatus != "ALL":
        stmt = stmt.where(Tenant.status == boundaryStatus)
    if search and search.strip():
        stmt = stmt.where(or_(Tenant.name.ilike(f"%{search.strip()}%"), Tenant.tenant_id.ilike(f"%{search.strip()}%")))
    tenants = (await db.scalars(stmt.offset(skip).limit(limit))).all()
    rows = []
    for t in tenants:
        wards = await db.scalar(select(func.count(Ward.id)).where(Ward.tenant_id == t.tenant_id)) or 0
        mapped = await db.scalar(select(func.count(Ward.id)).where(Ward.tenant_id == t.tenant_id, Ward.boundary_geometry.isnot(None))) or 0
        parcels = await db.scalar(select(func.count(PropertyParcel.id)).where(PropertyParcel.tenant_id == t.tenant_id)) or 0
        layers = await db.scalar(select(func.count(GisLayerModel.id)).where(GisLayerModel.tenant_id == t.tenant_id)) or 0
        synced = await db.scalar(select(func.max(GisLayerModel.last_synced_at)).where(GisLayerModel.tenant_id == t.tenant_id))
        rows.append(
            GisScopeRow(
                tenantId=t.tenant_id, tenantName=t.name, stateCode=t.state_code, district=t.district or "", status=t.status or "",
                wardCount=wards, wardBoundaryCount=mapped, parcelCount=parcels, layerCount=layers, lastSyncedAt=synced,
            )
        )
    return ApiResponse(data=rows)


@router.get("/boundaries")
async def get_boundaries(
    tenantId: str = Query(...),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    tenant = await _authorized_ulb(tenantId, user, db)
    wards = (await db.scalars(select(Ward).where(Ward.tenant_id == tenant.tenant_id, Ward.boundary_geometry.isnot(None)))).all()
    return _feature_collection([
        {"type": "Feature", "geometry": w.boundary_geometry, "properties": {"name": w.ward_name, "wardNumber": w.ward_number, "tenantId": w.tenant_id}}
        for w in wards
    ])


# Layers


@router.get("/layers", response_model=ApiResponse[List[GisLayerResponse]])
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
    stmt = select(GisLayerModel, Tenant.name).join(Tenant, Tenant.tenant_id == GisLayerModel.tenant_id).order_by(GisLayerModel.layer_name)
    if tenantId:
        stmt = stmt.where(GisLayerModel.tenant_id == (await _authorized_ulb(tenantId, user, db)).tenant_id)
    elif not is_super_admin(user):
        stmt = stmt.where(tenant_scope_filter(user))
    if category:
        stmt = stmt.where(GisLayerModel.layer_category.in_(_split(category)))
    if utilityCategory:
        stmt = stmt.where(GisLayerModel.utility_category.in_(_split(utilityCategory)))
    if layerStatus:
        stmt = stmt.where(GisLayerModel.layer_status == layerStatus)
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(GisLayerModel.layer_name.ilike(term), GisLayerModel.layer_code.ilike(term)))
    rows = (await db.execute(stmt.offset(skip).limit(limit))).all()
    counts = dict((await db.execute(
        select(GisFeatureModel.layer_id, func.count(GisFeatureModel.id))
        .where(GisFeatureModel.layer_id.in_([l.id for l, _ in rows]))
        .group_by(GisFeatureModel.layer_id)
    )).all()) if rows else {}
    return ApiResponse(data=[_layer_response(l, name, counts.get(l.id, 0)) for l, name in rows])


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
    code = payload.layerCode.strip().upper()
    if await db.scalar(select(GisLayerModel.id).where(GisLayerModel.tenant_id == tenant.tenant_id, GisLayerModel.layer_code == code)):
        raise HTTPException(status_code=400, detail=f"Layer code '{code}' already exists for this ULB.")
    layer = GisLayerModel(tenant_id=tenant.tenant_id, state_code=tenant.state_code)
    await _apply_layer(layer, payload)
    db.add(layer)
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
    await _apply_layer(layer, payload)
    await db.commit()
    await db.refresh(layer)
    tenant = await db.scalar(select(Tenant).where(Tenant.tenant_id == layer.tenant_id))
    count = await db.scalar(select(func.count(GisFeatureModel.id)).where(GisFeatureModel.layer_id == layer.id)) or 0
    return ApiResponse(data=_layer_response(layer, tenant.name if tenant else "", count))


@router.delete("/layers/{layer_id}", response_model=ApiResponse[dict])
async def delete_layer(layer_id: str, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    layer = await _authorized_layer(layer_id, user, db)
    await db.delete(layer)
    await db.commit()
    return ApiResponse(data={"id": layer_id})


@router.post("/layers/{layer_id}/features", response_model=ApiResponse[GisImportResult])
async def import_features(layer_id: str, payload: GisImportPayload, user: dict = Depends(manage_layers), db: AsyncSession = Depends(get_write_db)):
    """Replaces a stored layer's features from GeoJSON, transforming them to EPSG:4326."""
    layer = await _authorized_layer(layer_id, user, db)
    if layer.data_source in REMOTE_SOURCES:
        raise HTTPException(status_code=409, detail="WMS and WFS layers are read from their service.")
    srid = _srid(payload.sourceCrs)
    collection = payload.featureCollection
    features = collection.get("features") if collection.get("type") == "FeatureCollection" else None
    if not isinstance(features, list):
        raise HTTPException(status_code=422, detail="Upload a GeoJSON FeatureCollection.")
    if len(features) > MAX_IMPORT_FEATURES:
        raise HTTPException(status_code=422, detail=f"Import at most {MAX_IMPORT_FEATURES} features at a time.")
    await db.execute(text("DELETE FROM gis_features WHERE layer_id = :layer"), {"layer": layer.id})
    imported = rejected = 0
    insert = text(
        "INSERT INTO gis_features (id, layer_id, tenant_id, feature_ref, properties, geom, created_at) "
        "SELECT :id, :layer, :tenant, :ref, CAST(:props AS json), "
        "ST_Transform(ST_SetSRID(g, :srid), 4326), now() "
        "FROM (SELECT ST_GeomFromGeoJSON(:geometry) AS g) s WHERE ST_IsValid(g)"
    )
    for feature in features:
        geometry = feature.get("geometry") if isinstance(feature, dict) else None
        if not geometry:
            rejected += 1
            continue
        properties = feature.get("properties") or {}
        try:
            async with db.begin_nested():
                result = await db.execute(insert, {
                    "id": str(uuid.uuid4()),
                    "layer": layer.id,
                    "tenant": layer.tenant_id,
                    "ref": str(feature.get("id") or properties.get("id") or "")[:100] or None,
                    "props": json.dumps(properties),
                    "srid": srid,
                    "geometry": json.dumps(geometry),
                })
            if result.rowcount:
                imported += 1
            else:
                rejected += 1
        except Exception:
            rejected += 1
    layer.last_synced_at = datetime.datetime.utcnow()
    await db.commit()
    return ApiResponse(data=GisImportResult(imported=imported, rejected=rejected))


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
    for value, field, name in (
        (assetStatus, "assetStatus", "asset"),
        (roadCategory, "roadCategory", "road"),
        (roadStatus, "roadStatus", "state"),
        (roadSurface, "surface", "surface"),
        (zone, "zone", "zone"),
        (ward, "ward", "ward"),
    ):
        if value:
            any_of(f"f.properties->>'{field}'", _split(value), name)
    if minWidth is not None:
        clauses.append("(f.properties->>'width')::float >= :min_width")
        params["min_width"] = minWidth
    if maxWidth is not None:
        clauses.append("(f.properties->>'width')::float <= :max_width")
        params["max_width"] = maxWidth
    if bbox:
        try:
            min_lon, min_lat, max_lon, max_lat = [float(v) for v in bbox.split(",")]
        except ValueError:
            raise HTTPException(status_code=422, detail="bbox must be minLon,minLat,maxLon,maxLat.")
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


@router.get("/parcels")
async def query_parcels(
    tenantId: str = Query(...),
    wards: Optional[str] = Query(None),
    categories: Optional[str] = Query(None),
    statuses: Optional[str] = Query(None),
    gisStatus: Optional[str] = Query(None, description="mapped or unmapped"),
    search: Optional[str] = Query(None),
    limit: int = Query(1000, ge=1, le=MAX_FEATURES),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_read_db),
):
    """Parcels hold point coordinates today, so they are returned as points."""
    tenant = await _authorized_ulb(tenantId, user, db)
    stmt = select(PropertyParcel, Ward.ward_name).outerjoin(Ward, Ward.id == PropertyParcel.ward_id).where(PropertyParcel.tenant_id == tenant.tenant_id).order_by(PropertyParcel.ulpin)
    if wards:
        stmt = stmt.where(PropertyParcel.ward_id.in_(_split(wards)))
    if gisStatus == "unmapped":
        return _feature_collection([]) | {"unmapped": await db.scalar(select(func.count(PropertyParcel.id)).where(PropertyParcel.tenant_id == tenant.tenant_id, PropertyParcel.latitude.is_(None))) or 0}
    stmt = stmt.where(PropertyParcel.latitude.isnot(None), PropertyParcel.longitude.isnot(None))
    unit_filters = []
    if categories:
        unit_filters.append(PropertyUnit.usage_category.in_(_split(categories)))
    if statuses:
        unit_filters.append(PropertyUnit.tax_status.in_(_split(statuses)))
    if unit_filters:
        stmt = stmt.where(
            select(PropertyUnit.id).join(Building, PropertyUnit.building_id == Building.id)
            .where(Building.parcel_id == PropertyParcel.id, *unit_filters).exists()
        )
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(or_(PropertyParcel.ulpin.ilike(term), PropertyParcel.survey_number.ilike(term)))
    rows = (await db.execute(stmt.limit(limit + 1))).all()
    return _feature_collection(
        [
            {
                "type": "Feature",
                "id": p.id,
                "geometry": {"type": "Point", "coordinates": [p.longitude, p.latitude]},
                "properties": {"ulpin": p.ulpin, "surveyNumber": p.survey_number, "address": p.address, "ward": ward_name, "_layer": "Registered Parcels", "_category": "Parcel"},
            }
            for p, ward_name in rows[:limit]
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


@router.post("/workspaces", response_model=ApiResponse[GisWorkspaceResponse], status_code=status.HTTP_201_CREATED)
async def save_workspace(payload: GisWorkspacePayload, user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_write_db)):
    _srid(payload.crs)
    for ulb in payload.ulbTenants:
        await ensure_tenant_access(ulb, user, db)
    workspace = GisWorkspaceModel(
        owner=_workspace_owner(user), workspace_name=payload.workspaceName or "Untitled workspace", geographic_scope=payload.geographicScope,
        state_tenants=payload.stateTenants, ulb_tenants=payload.ulbTenants, map_extent=payload.mapExtent, base_map=payload.baseMap, crs=payload.crs,
        default_zoom=payload.defaultZoom, default_centre=payload.defaultCentre, visible_layers=payload.visibleLayers, refresh_interval=payload.refreshInterval,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return ApiResponse(data=_workspace_response(workspace))
