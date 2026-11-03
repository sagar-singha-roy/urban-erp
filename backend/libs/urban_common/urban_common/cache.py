import json
import logging
from typing import Any, Optional

import valkey.asyncio as aiovalkey

from urban_common.settings import settings

logger = logging.getLogger(__name__)


def scoped_key(tenant_id: str, sub_tenant_id: Optional[str], resource: str) -> str:
    return f"stats:tenant:{tenant_id}:sub:{sub_tenant_id or 'ALL'}:{resource}"


class ValkeyClient:
    def __init__(self):
        self.client: Optional[aiovalkey.Valkey] = None

    async def connect(self):
        try:
            self.client = aiovalkey.from_url(settings.VALKEY_URL, decode_responses=True, socket_timeout=2.0)
            await self.client.ping()
        except Exception as e:
            logger.warning("Valkey connection failed: %s. Continuing without a cache.", e)
            self.client = None

    async def close(self):
        if self.client:
            await self.client.aclose()

    async def get(self, key: str) -> Any:
        if not self.client:
            return None
        try:
            value = await self.client.get(key)
            return json.loads(value) if value else None
        except Exception as e:
            logger.warning("Valkey get failed for %s: %s", key, e)
            return None

    async def set(self, key: str, value: Any, expire_seconds: int = 300) -> None:
        if not self.client:
            return
        try:
            await self.client.set(key, json.dumps(value), ex=expire_seconds)
        except Exception as e:
            logger.warning("Valkey set failed for %s: %s", key, e)

    async def delete(self, key: str) -> None:
        if not self.client:
            return
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.warning("Valkey delete failed for %s: %s", key, e)


valkey_client = ValkeyClient()
