"""Caching layer for VoyageMind.

Uses Redis when available, falls back to an in-memory dict.
All external API calls should be cached to minimize rate-limit hits.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# In-memory fallback cache
_memory_cache: dict[str, str] = {}
_redis_client = None


async def _get_redis():
    """Lazily connect to Redis; returns None if unavailable."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis.asyncio as aioredis

        settings = get_settings()
        _redis_client = aioredis.from_url(settings.redis_url, decode_responses=True)
        await _redis_client.ping()
        logger.info("Connected to Redis at %s", settings.redis_url)
        return _redis_client
    except Exception:
        logger.warning("Redis unavailable — using in-memory cache.")
        return None


async def cache_result(key: str, data: Any, ttl: int | None = None) -> None:
    """Store a JSON-serializable value in cache."""
    settings = get_settings()
    ttl = ttl or settings.cache_ttl_seconds
    payload = json.dumps(data, default=str)

    redis = await _get_redis()
    if redis:
        await redis.set(key, payload, ex=ttl)
    else:
        _memory_cache[key] = payload


async def get_cached_result(key: str) -> Any | None:
    """Retrieve a cached value, or None if absent."""
    redis = await _get_redis()
    if redis:
        raw = await redis.get(key)
    else:
        raw = _memory_cache.get(key)

    if raw is None:
        return None
    return json.loads(raw)