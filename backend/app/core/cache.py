"""
VoyageMind Cache Module

Provides Redis-based caching for API responses, model outputs, and session data.
Supports expiration, key patterns, and atomic operations.
"""

import json
import logging
from typing import Any, Optional, List
import redis
from datetime import datetime, timedelta

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis cache manager for VoyageMind.
    
    Handles:
    - Caching external API responses (flights, hotels, weather)
    - Session data storage
    - Prompt/response caching
    - TTL-based expiration
    """

    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_url = settings.redis.url
            self.ttl = settings.redis.ttl
            
            # Parse Redis URL and create connection
            self.client = redis.from_url(
                self.redis_url,
                max_connections=settings.redis.max_connections,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {self.redis_url}")
            
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {str(e)}")
            self.client = None

    def is_connected(self) -> bool:
        """
        Check if Redis connection is active.
        
        Returns:
            True if connected, False otherwise
        """
        if self.client is None:
            return False
        
        try:
            self.client.ping()
            return True
        except redis.ConnectionError:
            return False

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a key-value pair in cache.
        
        Args:
            key: Cache key
            value: Value (will be JSON serialized)
            ttl: Time to live in seconds (uses default if None)
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            logger.warning(f"Redis not connected, skipping cache for key: {key}")
            return False
        
        try:
            ttl = ttl or self.ttl
            serialized = json.dumps(value)
            self.client.setex(key, ttl, serialized)
            logger.debug(f"Cached key: {key} (TTL: {ttl}s)")
            return True
            
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to cache key {key}: {str(e)}")
            return False

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if not self.is_connected():
            return None
        
        try:
            value = self.client.get(key)
            if value:
                logger.debug(f"Cache hit: {key}")
                return json.loads(value)
            else:
                logger.debug(f"Cache miss: {key}")
                return None
                
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to retrieve from cache {key}: {str(e)}")
            return None

    def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if deleted, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            result = self.client.delete(key)
            logger.debug(f"Deleted cache key: {key}")
            return result > 0
            
        except redis.RedisError as e:
            logger.warning(f"Failed to delete cache key {key}: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if exists, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            return self.client.exists(key) > 0
            
        except redis.RedisError:
            return False

    def get_many(self, keys: List[str]) -> dict:
        """
        Get multiple values from cache.
        
        Args:
            keys: List of cache keys
            
        Returns:
            Dictionary with {key: value} pairs only for found keys
        """
        if not self.is_connected():
            return {}
        
        try:
            values = self.client.mget(keys)
            result = {}
            
            for key, value in zip(keys, values):
                if value:
                    try:
                        result[key] = json.loads(value)
                    except json.JSONDecodeError:
                        pass
            
            return result
            
        except redis.RedisError as e:
            logger.warning(f"Failed to get multiple keys: {str(e)}")
            return {}

    def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """
        Set multiple key-value pairs in cache.
        
        Args:
            mapping: Dictionary of key-value pairs
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            ttl = ttl or self.ttl
            
            for key, value in mapping.items():
                serialized = json.dumps(value)
                self.client.setex(key, ttl, serialized)
            
            logger.debug(f"Cached {len(mapping)} items")
            return True
            
        except (redis.RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Failed to set multiple cache items: {str(e)}")
            return False

    def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Key pattern (e.g., "flights:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.is_connected():
            return 0
        
        try:
            keys = self.client.keys(pattern)
            if keys:
                deleted = self.client.delete(*keys)
                logger.debug(f"Cleared {deleted} cache keys matching pattern: {pattern}")
                return deleted
            return 0
            
        except redis.RedisError as e:
            logger.warning(f"Failed to clear cache pattern {pattern}: {str(e)}")
            return 0

    def flush_all(self) -> bool:
        """
        Clear entire cache (use with caution!).
        
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected():
            return False
        
        try:
            self.client.flushdb()
            logger.warning("Flushed entire Redis cache!")
            return True
            
        except redis.RedisError as e:
            logger.warning(f"Failed to flush cache: {str(e)}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache info
        """
        if not self.is_connected():
            return {"status": "disconnected"}
        
        try:
            info = self.client.info()
            return {
                "status": "connected",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "evicted_keys": info.get("evicted_keys"),
            }
            
        except redis.RedisError:
            return {"status": "error"}


# Cache key prefixes for consistency
class CacheKeys:
    """Cache key patterns"""
    
    FLIGHTS = "flights:{origin}:{destination}:{date}"
    HOTELS = "hotels:{location}:{checkin}:{checkout}"
    WEATHER = "weather:{location}:{date}"
    ATTRACTION = "attraction:{id}"
    SESSION = "session:{session_id}"
    TRIP = "trip:{trip_id}"
    USER_PREFS = "user_prefs:{user_id}"
    AGENT_PLAN = "agent_plan:{trip_id}"


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """
    Get or create cache manager instance (singleton).
    
    Returns:
        CacheManager instance
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager
