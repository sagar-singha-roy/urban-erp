import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

class RedisClient:
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        try:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0
            )
            await self.redis.ping()
            logger.info("Connected to Redis successfully.")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Fallback to in-memory/bypass.")
            self.redis = None

    async def close(self):
        if self.redis:
            await self.redis.close()

    async def get(self, key: str) -> Optional[Any]:
        if not self.redis:
            return None
        try:
            val = await self.redis.get(key)
            if val:
                return json.loads(val)
        except Exception as e:
            logger.warning(f"Redis get failed for {key}: {e}")
        return None

    async def set(self, key: str, value: Any, expire_seconds: int = 300):
        if not self.redis:
            return
        try:
            await self.redis.set(key, json.dumps(value), ex=expire_seconds)
        except Exception as e:
            logger.warning(f"Redis set failed for {key}: {e}")

    async def delete(self, key: str):
        if not self.redis:
            return
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed for {key}: {e}")

redis_client = RedisClient()
