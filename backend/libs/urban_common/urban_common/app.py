import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Iterable, Optional

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from urban_common.cache import valkey_client
from urban_common.db import engine
from urban_common.events import relay_loop
from urban_common.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("urban-module")


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
            started = started or message["type"] == "http.response.start"
            await send(message)

        try:
            await self.inner(scope, receive, tracking_send)
        except Exception:
            logger.exception("Unhandled error on %s %s", scope.get("method"), scope.get("path"))
            if started:
                raise
            await JSONResponse({"detail": "The server could not complete this request."}, status_code=500)(scope, receive, send)


def create_service_app(module_code: str, module_name: str, routers: Optional[Iterable[APIRouter]] = None, publishes_events: bool = False) -> FastAPI:
    service = f"{module_code.lower()}-service"

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await valkey_client.connect()
        relay = asyncio.create_task(relay_loop(service)) if publishes_events else None
        yield
        if relay:
            relay.cancel()
            await asyncio.gather(relay, return_exceptions=True)
        await valkey_client.close()
        await engine.dispose()

    app = FastAPI(
        title=f"Urban {module_name} Service",
        openapi_url=f"{settings.API_V1_STR}/openapi.json" if settings.is_development else None,
        docs_url="/docs" if settings.is_development else None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(ServerErrorResponder)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for router in routers or []:
        app.include_router(router, prefix=settings.API_V1_STR)

    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "UP", "service": service, "module": module_code}

    return app
