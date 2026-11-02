import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.valkey import valkey_client
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.db.rls import app_role_bypasses_rls, apply_rls
from app.db.session import engine, Base
from app.api.v1.iam import _seed_standard_roles_if_empty
from app.core.backup_runner import scheduler_loop
from app.core.request_metrics import record_response
from app.core.white_label_worker import white_label_loop
from app.core.api_quota import ApiMeteringMiddleware
from app.core.quota_worker import ensure_default_levels, quota_loop
from app.db.seed import seed_initial_data
from app.api.v1.boundaries import router as boundaries_router
from app.api.v1.auth import router as auth_router
from app.api.v1.tenants import router as tenants_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("urban-core")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing Urban Core Service...")
    # Connect Valkey
    await valkey_client.connect()
    
    # Schema, policies and seed data use the owner role. Requests never do.
    admin_engine = create_async_engine(settings.admin_db_url)
    try:
        async with admin_engine.begin() as conn:
            # Other environments get their schema from Alembic migrations.
            if settings.is_development:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis"))
                await conn.run_sync(Base.metadata.create_all)
            await apply_rls(conn)
        async with AsyncSession(admin_engine, expire_on_commit=False) as session:
            await seed_initial_data(session)
            await _seed_standard_roles_if_empty(session)
            await ensure_default_levels(session)
    except Exception as e:
        logger.exception("Database bootstrap failed: %s", e)
        if not settings.is_development:
            raise
    finally:
        await admin_engine.dispose()

    async with engine.connect() as conn:
        if await app_role_bypasses_rls(conn):
            message = "The application database role bypasses row-level security."
            if not settings.is_development:
                raise RuntimeError(message)
            logger.error(message)

    scheduler = asyncio.create_task(scheduler_loop())
    white_label = asyncio.create_task(white_label_loop())
    quota = asyncio.create_task(quota_loop())

    yield

    scheduler.cancel()
    white_label.cancel()
    quota.cancel()

    # Cleanup
    await valkey_client.close()
    await engine.dispose()
    logger.info("Urban Core Service shutdown complete.")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.is_development else None,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
    lifespan=lifespan
)

class ServerErrorResponder:
    """Sits inside CORS so unexpected errors reach the browser as a readable 500."""

    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.inner(scope, receive, send)
            return
        started = False

        async def tracking_send(message):
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
                record_response(message["status"])
            await send(message)

        try:
            await self.inner(scope, receive, tracking_send)
        except Exception:
            logger.exception("Unhandled error on %s %s", scope.get("method"), scope.get("path"))
            if started:
                raise
            record_response(500)
            response = JSONResponse({"detail": "The server could not complete this request."}, status_code=500)
            await response(scope, receive, send)


app.add_middleware(ServerErrorResponder)
app.add_middleware(ApiMeteringMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.v1.admin import router as admin_router
from app.api.v1.ulbs import router as ulbs_router
from app.api.v1.tenant_lifecycle import router as tenant_lifecycle_router
from app.api.v1.modules import router as modules_router
from app.api.v1.subscriptions import router as subscriptions_router
from app.api.v1.delegation import router as delegation_router
from app.api.v1.iam import router as iam_router
from app.api.v1.security import router as security_router
from app.api.v1.audit_vault import router as audit_vault_router
from app.api.v1.fleet import router as fleet_router
from app.api.v1.backup_dr import router as backup_dr_router
from app.api.v1.executive import router as executive_router
from app.api.v1.gis import router as gis_router
from app.api.v1.white_label import public_router as white_label_public_router, router as white_label_router
from app.api.v1.white_label_domains import router as white_label_domains_router
from app.api.v1.quotas import public_router as quotas_public_router, router as quotas_router
from app.api.v1.quota_alerts import router as quota_alerts_router

# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(tenants_router, prefix=settings.API_V1_STR)
app.include_router(ulbs_router, prefix=settings.API_V1_STR)
app.include_router(tenant_lifecycle_router, prefix=settings.API_V1_STR)
app.include_router(subscriptions_router, prefix=settings.API_V1_STR)
app.include_router(delegation_router, prefix=settings.API_V1_STR)
app.include_router(modules_router, prefix=settings.API_V1_STR)
app.include_router(iam_router, prefix=settings.API_V1_STR)
app.include_router(security_router, prefix=settings.API_V1_STR)
app.include_router(audit_vault_router, prefix=settings.API_V1_STR)
app.include_router(fleet_router, prefix=settings.API_V1_STR)
app.include_router(backup_dr_router, prefix=settings.API_V1_STR)
app.include_router(gis_router, prefix=settings.API_V1_STR)
app.include_router(white_label_public_router, prefix=settings.API_V1_STR)
app.include_router(white_label_router, prefix=settings.API_V1_STR)
app.include_router(white_label_domains_router, prefix=settings.API_V1_STR)
app.include_router(quotas_public_router, prefix=settings.API_V1_STR)
app.include_router(quotas_router, prefix=settings.API_V1_STR)
app.include_router(quota_alerts_router, prefix=settings.API_V1_STR)
app.include_router(executive_router, prefix=settings.API_V1_STR)
app.include_router(boundaries_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "UP",
        "service": "urban-core-service",
        "environment": settings.ENVIRONMENT
    }
