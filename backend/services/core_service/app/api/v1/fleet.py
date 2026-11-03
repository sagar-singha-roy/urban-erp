"""Fleet health measured when requested. Nothing here reports a figure it did not observe."""
import asyncio
import datetime
import time
from typing import List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import request_metrics
from app.core.auth import require_roles
from app.core.config import settings
from app.core.valkey import valkey_client
from app.db.models import MicroserviceRegistryModel
from app.db.session import get_read_db, get_write_db, read_engine, write_engine
from app.schemas.fleet import (
    DatabaseConnectionPoolResponse,
    MicroserviceOverviewStats,
    MicroserviceRegisterPayload,
    MicroserviceRegistryResponse,
    PodMonitoringResponse,
    WorkerQueueResponse,
)
from app.schemas.tenant import ApiResponse

router = APIRouter(prefix="/fleet/cluster", tags=["ADM-O01 Platform Fleet & Microservice Cluster Health"], dependencies=[Depends(require_roles(["super_admin"]))])

SERVICE_STARTED_AT = datetime.datetime.utcnow()
HEALTHY, DEGRADED, UNAVAILABLE = "Healthy", "Degraded", "Unavailable"


async def _probe_http(url: str, timeout: float) -> Tuple[str, Optional[float]]:
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url)
    except httpx.HTTPError:
        return UNAVAILABLE, None
    latency = round((time.perf_counter() - started) * 1000, 1)
    return (HEALTHY if response.is_success else DEGRADED), latency


async def _probe_database(db: AsyncSession) -> Tuple[str, Optional[float]]:
    started = time.perf_counter()
    await db.execute(text("SELECT 1"))
    return HEALTHY, round((time.perf_counter() - started) * 1000, 1)


async def _probe_valkey() -> Tuple[str, Optional[float]]:
    if not valkey_client.client:
        return UNAVAILABLE, None
    started = time.perf_counter()
    try:
        await valkey_client.client.ping()
    except Exception:
        return UNAVAILABLE, None
    return HEALTHY, round((time.perf_counter() - started) * 1000, 1)


def _service(code: str, name: str, description: str, category: str, base_url: str, method: str, endpoint: str, status: str, latency: Optional[float], measured: bool = False) -> MicroserviceRegistryResponse:
    return MicroserviceRegistryResponse(
        id=f"builtin-{code.lower()}",
        serviceCode=code,
        serviceName=name,
        serviceDescription=description,
        serviceCategory=category,
        serviceType="Dependency",
        environments=[settings.ENVIRONMENT],
        baseUrl=base_url,
        healthCheckEndpoint=endpoint,
        healthCheckMethod=method,
        healthCheckIntervalSeconds=0,
        timeoutSeconds=3,
        retryCount=0,
        criticalityLevel="P0 - Critical",
        monitoringEnabled=True,
        status=status,
        version="",
        region="",
        avgLatencyMs=latency,
        errorRatePct=request_metrics.error_rate_pct() if measured else None,
        cpuUsagePct=request_metrics.cpu_pct() if measured else None,
        memoryUsagePct=request_metrics.memory_pct() if measured else None,
        createdAt=SERVICE_STARTED_AT,
    )


def _registered(record: MicroserviceRegistryModel, status: str, latency: Optional[float]) -> MicroserviceRegistryResponse:
    return MicroserviceRegistryResponse(
        id=record.id,
        serviceCode=record.service_code,
        serviceName=record.service_name,
        serviceDescription=record.service_description,
        serviceCategory=record.service_category,
        serviceType=record.service_type,
        environments=record.environments or [],
        baseUrl=record.base_url,
        healthCheckEndpoint=record.health_check_endpoint,
        healthCheckMethod=record.health_check_method,
        healthCheckIntervalSeconds=record.health_check_interval_seconds,
        timeoutSeconds=record.timeout_seconds,
        retryCount=record.retry_count,
        criticalityLevel=record.criticality_level,
        monitoringEnabled=record.monitoring_enabled,
        alertPolicy=record.alert_policy,
        status=status,
        version=record.version,
        region=record.region,
        avgLatencyMs=latency,
        createdAt=record.created_at,
        updatedAt=record.updated_at,
    )


async def _measure_builtin(db: AsyncSession) -> List[MicroserviceRegistryResponse]:
    database = make_url(settings.write_db_url)
    db_probe = await _probe_database(db)
    valkey_probe, keycloak_probe = await asyncio.gather(
        _probe_valkey(),
        _probe_http(f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}", 3.0),
    )
    return [
        _service("CORE-API", settings.PROJECT_NAME, "This API instance, which is answering this request.", "Core Platform", "", "GET", "/health", HEALTHY, None, measured=True),
        _service("POSTGRES", "PostgreSQL", "Primary database connection.", "Data", f"{database.host}:{database.port or 5432}", "SQL", "SELECT 1", *db_probe),
        _service("VALKEY", "Valkey Cache", "Shared cache connection.", "Data", "", "REDIS", "PING", *valkey_probe),
        _service("KEYCLOAK", "Keycloak", "Identity provider realm endpoint.", "Identity", settings.KEYCLOAK_URL, "GET", f"/realms/{settings.KEYCLOAK_REALM}", *keycloak_probe),
    ]


async def _measure_registered(records: List[MicroserviceRegistryModel]) -> List[MicroserviceRegistryResponse]:
    probes = await asyncio.gather(
        *(_probe_http(f"{r.base_url.rstrip('/')}{r.health_check_endpoint}", float(r.timeout_seconds or 3)) for r in records)
    )
    return [_registered(record, status, latency) for record, (status, latency) in zip(records, probes)]


@router.get("/stats", response_model=ApiResponse[MicroserviceOverviewStats])
async def get_cluster_stats(db: AsyncSession = Depends(get_read_db)):
    records = (await db.scalars(select(MicroserviceRegistryModel))).all()
    services = await _measure_builtin(db) + await _measure_registered(list(records))
    latencies = [s.avgLatencyMs for s in services if s.avgLatencyMs is not None]
    connections = await db.scalar(
        text("SELECT count(*) FROM pg_stat_activity WHERE datname = current_database()")
    )
    return ApiResponse(
        data=MicroserviceOverviewStats(
            totalServices=len(services),
            healthyServices=sum(1 for s in services if s.status == HEALTHY),
            degradedServices=sum(1 for s in services if s.status == DEGRADED),
            unavailableServices=sum(1 for s in services if s.status == UNAVAILABLE),
            averageResponseTimeMs=round(sum(latencies) / len(latencies), 1) if latencies else None,
            activeDbConnections=connections or 0,
            errorRatePct=request_metrics.error_rate_pct(),
            cpuUtilisationPct=request_metrics.cpu_pct(),
            memoryUtilisationPct=request_metrics.memory_pct(),
        )
    )


@router.get("/services", response_model=ApiResponse[List[MicroserviceRegistryResponse]])
async def list_microservices(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_read_db),
):
    stmt = select(MicroserviceRegistryModel).order_by(MicroserviceRegistryModel.service_code)
    records = (await db.scalars(stmt)).all()
    services = await _measure_builtin(db) + await _measure_registered(list(records))
    if category and category != "ALL":
        services = [s for s in services if s.serviceCategory == category]
    if status_filter and status_filter != "ALL":
        services = [s for s in services if s.status == status_filter]
    if search and search.strip():
        term = search.strip().lower()
        services = [s for s in services if term in f"{s.serviceCode} {s.serviceName} {s.serviceDescription}".lower()]
    return ApiResponse(data=services[skip : skip + limit])


@router.post("/services", response_model=ApiResponse[MicroserviceRegistryResponse])
async def register_microservice(payload: MicroserviceRegisterPayload, db: AsyncSession = Depends(get_write_db)):
    code = payload.serviceCode.strip().upper()
    if await db.scalar(select(MicroserviceRegistryModel.id).where(MicroserviceRegistryModel.service_code == code)):
        raise HTTPException(status_code=400, detail=f"Service with code '{code}' is already registered.")
    record = MicroserviceRegistryModel(
        service_code=code,
        service_name=payload.serviceName.strip(),
        service_description=payload.serviceDescription.strip(),
        service_category=payload.serviceCategory,
        service_type=payload.serviceType,
        environments=payload.environments,
        base_url=payload.baseUrl.strip(),
        health_check_endpoint=payload.healthCheckEndpoint.strip(),
        health_check_method=payload.healthCheckMethod,
        health_check_interval_seconds=payload.healthCheckIntervalSeconds,
        timeout_seconds=payload.timeoutSeconds,
        retry_count=payload.retryCount,
        criticality_level=payload.criticalityLevel,
        monitoring_enabled=payload.monitoringEnabled,
        alert_policy=payload.alertPolicy,
        version=payload.version,
        region=payload.region,
        status="Unknown",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    (service,) = await _measure_registered([record])
    return ApiResponse(data=service)


@router.get("/pods", response_model=ApiResponse[List[PodMonitoringResponse]])
async def list_pods():
    """No orchestrator is connected, so there are no pods to report."""
    return ApiResponse(data=[])


@router.get("/queues", response_model=ApiResponse[List[WorkerQueueResponse]])
async def list_worker_queues():
    """The platform has no worker queues yet."""
    return ApiResponse(data=[])


@router.get("/db-pools", response_model=ApiResponse[List[DatabaseConnectionPoolResponse]])
async def list_database_connection_pools(db: AsyncSession = Depends(get_read_db)):
    """Live pool counters from this API instance."""
    _, latency = await _probe_database(db)
    pools = []
    for name, engine in (("Write pool", write_engine), ("Read pool", read_engine)):
        pool = engine.pool
        url = engine.url
        pools.append(
            DatabaseConnectionPoolResponse(
                id=name.lower().replace(" ", "-"),
                poolName=name,
                databaseCluster=f"{url.host}:{url.port or 5432}",
                databaseName=url.database or "",
                serviceName=settings.PROJECT_NAME,
                connectionStatus="Connected",
                activeConnections=pool.checkedout(),
                idleConnections=pool.checkedin(),
                maxPoolSize=pool.size() + pool._max_overflow,
                queryLatencyP95Ms=latency,
                alertThresholdPct=0,
                createdAt=SERVICE_STARTED_AT,
            )
        )
    return ApiResponse(data=pools)

