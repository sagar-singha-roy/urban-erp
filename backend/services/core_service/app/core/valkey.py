import json
import logging
from typing import Any, Optional
import valkey.asyncio as aiovalkey
from app.core.config import settings

logger = logging.getLogger(__name__)

class ValkeyClient:
    def __init__(self):
        self.client: Optional[aiovalkey.Valkey] = None

    async def connect(self):
        try:
            self.client = aiovalkey.from_url(
                settings.VALKEY_URL,
                decode_responses=True,
                socket_timeout=2.0
            )
            await self.client.ping()
            logger.info("Connected to Valkey successfully.")
        except Exception as e:
            logger.warning(f"Valkey connection failed: {e}. Fallback to in-memory/bypass.")
            self.client = None

    async def close(self):
        if self.client:
            await self.client.close()

    async def get(self, key: str) -> Optional[Any]:
        if not self.client:
            return None
        try:
            val = await self.client.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Valkey get failed for {key}: {e}")
        return None

    async def set(self, key: str, value: Any, expire_seconds: int = 300):
        if not self.client:
            return
        try:
            await self.client.set(key, json.dumps(value), ex=expire_seconds)
        except Exception as e:
            logger.warning(f"Valkey set failed for {key}: {e}")

    async def delete(self, key: str):
        if not self.client:
            return
        try:
            await self.client.delete(key)
        except Exception as e:
            logger.warning(f"Valkey delete failed for {key}: {e}")

valkey_client = ValkeyClient()
