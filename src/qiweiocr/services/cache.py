from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


class CacheService:
    def __init__(self, redis_client: Redis, ttl_seconds: int, key_prefix: str) -> None:
        self.redis_client = redis_client
        self.ttl_seconds = ttl_seconds
        self.key_prefix = key_prefix

    def build_key(self, cache_suffix: str) -> str:
        return f"{self.key_prefix}{cache_suffix}"

    async def get_json(self, cache_suffix: str) -> dict[str, Any] | None:
        try:
            payload = await self.redis_client.get(self.build_key(cache_suffix))
            if not payload:
                return None
            if isinstance(payload, bytes):
                payload = payload.decode("utf-8")
            return json.loads(payload)
        except Exception as exc:
            logger.warning("Redis GET failed: %s", exc)
            return None

    async def set_json(self, cache_suffix: str, data: dict[str, Any]) -> None:
        try:
            await self.redis_client.set(
                self.build_key(cache_suffix),
                json.dumps(data, ensure_ascii=False),
                ex=self.ttl_seconds,
            )
        except Exception as exc:
            logger.warning("Redis SET failed: %s", exc)
