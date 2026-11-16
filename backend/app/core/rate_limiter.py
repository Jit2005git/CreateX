"""CreateX AI - Rate Limiter & Abuse Protection Module

Protects expensive AI generation endpoints against denial of service and quota exhaustion.
Architecture:
- Identity Strategy:
  * Primary: Authenticated user ID (user:<id>) or validated guest session (guest:<session_id>).
  * Supplementary: Client IP address (ip:<ip>) to prevent session cycling attacks.
- Dual Storage Strategy:
  * Distributed: Redis sorted-set sliding window when REDIS_URL is configured (ideal for multi-instance Cloud Run).
  * In-Memory: Thread-safe timestamp sliding window fallback when Redis is absent or transiently unavailable.
  * Fail-safe: Automatically falls back to in-memory store if Redis encounters connection errors.
- HTTP Contract:
  * Returns HTTP 429 Too Many Requests when limits are exceeded.
  * Attaches 'Retry-After' response header with seconds remaining.
  * Sanitizes error message (no leaked keys, IDs, or infrastructure details).
"""
import time
import uuid
import asyncio
import logging
from typing import Optional, Protocol, Tuple
from fastapi import Request, HTTPException, Depends, status

from app.core.config import settings
from app.core.auth import get_current_identity, AuthIdentity

logger = logging.getLogger(__name__)


# ─── STORE PROTOCOL & IMPLEMENTATIONS ─────────────────────────────────────────

class RateLimitStore(Protocol):
    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is permitted under rate limit and record usage.
        Returns:
            (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        ...

    async def clear(self) -> None:
        """Clear all stored counters (used primarily for test isolation)."""
        ...


class InMemoryRateLimitStore:
    """Thread-safe sliding-window in-memory store."""

    def __init__(self):
        self._records: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int]:
        now = time.time()
        window_start = now - window_seconds

        async with self._lock:
            timestamps = self._records.get(key, [])
            # Evict timestamps outside sliding window
            timestamps = [ts for ts in timestamps if ts > window_start]

            if len(timestamps) >= max_requests:
                # Earliest request determines when a slot frees up
                earliest = timestamps[0]
                retry_after = max(1, int(earliest + window_seconds - now))
                self._records[key] = timestamps
                return False, 0, retry_after

            timestamps.append(now)
            self._records[key] = timestamps
            remaining = max_requests - len(timestamps)
            return True, remaining, 0

    async def clear(self) -> None:
        async with self._lock:
            self._records.clear()


class RedisRateLimitStore:
    """Distributed Redis sliding-window store using sorted sets."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._redis = None
        self._fallback_store = InMemoryRateLimitStore()

    async def _get_client(self):
        if self._redis is None:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=2.0,
                socket_connect_timeout=2.0,
            )
        return self._redis

    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int]:
        redis_key = f"rate_limit:{key}"
        now = time.time()
        window_start = now - window_seconds

        try:
            client = await self._get_client()
            async with client.pipeline(transaction=True) as pipe:
                # 1. Remove expired timestamps
                pipe.zremrangebyscore(redis_key, 0, window_start)
                # 2. Count active timestamps in window
                pipe.zcard(redis_key)
                # 3. Retrieve earliest timestamp for Retry-After
                pipe.zrange(redis_key, 0, 0, withscores=True)
                results = await pipe.execute()

            current_count = results[1]
            earliest_items = results[2]

            if current_count >= max_requests:
                earliest_ts = earliest_items[0][1] if earliest_items else now
                retry_after = max(1, int(earliest_ts + window_seconds - now))
                return False, 0, retry_after

            # Record this request
            entry_id = f"{now}:{uuid.uuid4().hex[:8]}"
            async with client.pipeline(transaction=True) as pipe:
                pipe.zadd(redis_key, {entry_id: now})
                pipe.expire(redis_key, window_seconds + 5)
                await pipe.execute()

            remaining = max_requests - (current_count + 1)
            return True, max(0, remaining), 0

        except Exception as e:
            logger.warning(
                "Redis rate limit error (%s). Falling back to in-memory store.", e
            )
            return await self._fallback_store.check_and_increment(
                key, max_requests, window_seconds
            )

    async def clear(self) -> None:
        try:
            if self._redis:
                keys = await self._redis.keys("rate_limit:*")
                if keys:
                    await self._redis.delete(*keys)
        except Exception as e:
            logger.warning("Error clearing Redis rate limit store: %s", e)
        await self._fallback_store.clear()

    async def close(self) -> None:
        if self._redis:
            await self._redis.close()
            self._redis = None


# Global singleton store instance
_global_store: Optional[RateLimitStore] = None


def get_rate_limit_store() -> RateLimitStore:
    global _global_store
    if _global_store is None:
        if settings.redis_url and settings.redis_url.strip():
            logger.info("Initializing RedisRateLimitStore with REDIS_URL")
            _global_store = RedisRateLimitStore(settings.redis_url)
        else:
            if settings.is_production:
                logger.error(
                    "PRODUCTION INTEGRITY ALERT: REDIS_URL is not configured in production. "
                    "Rate limiting will operate in-memory per-instance, which cannot synchronize across scaled Cloud Run containers. "
                    "Configure REDIS_URL in Cloud Run environment variables to enable distributed abuse protection."
                )
            else:
                logger.info("Initializing InMemoryRateLimitStore for development")
            _global_store = InMemoryRateLimitStore()
    return _global_store


def set_rate_limit_store(store: RateLimitStore) -> None:
    """Override rate limit store (used for tests)."""
    global _global_store
    _global_store = store


# ─── FASTAPI DEPENDENCY ───────────────────────────────────────────────────────

class RateLimiter:
    """
    FastAPI dependency that enforces primary (User/Session) and supplementary (IP) rate limits.
    """

    def __init__(self, limit_type: str):
        """
        limit_type: "campaign" or "visual"
        """
        self.limit_type = limit_type

    def _get_client_ip(self, request: Request) -> str:
        # Respect reverse proxy X-Forwarded-For if present
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
            if ip:
                return ip
        if request.client and request.client.host:
            return request.client.host
        return "127.0.0.1"

    async def __call__(
        self,
        request: Request,
        identity: AuthIdentity = Depends(get_current_identity),
    ) -> bool:
        if not settings.rate_limit_enabled:
            return True

        store = get_rate_limit_store()
        client_ip = self._get_client_ip(request)

        # 1. Determine Primary Identity & Limit
        if identity.is_authenticated and identity.user_id:
            entity_key = f"user:{identity.user_id}"
            if self.limit_type == "campaign":
                primary_limit = settings.rate_limit_campaign_auth_per_minute
            else:
                primary_limit = settings.rate_limit_visual_auth_per_minute
        else:
            session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
            if session_id and session_id.strip():
                entity_key = f"guest:{session_id.strip()}"
            else:
                entity_key = f"anon:{client_ip}"

            if self.limit_type == "campaign":
                primary_limit = settings.rate_limit_campaign_per_minute
            else:
                primary_limit = settings.rate_limit_visual_per_minute

        # 2. Check Primary Rate Limit
        full_primary_key = f"{self.limit_type}:{entity_key}"
        allowed, remaining, retry_after = await store.check_and_increment(
            full_primary_key, primary_limit, window_seconds=60
        )
        if not allowed:
            logger.warning(
                "Rate limit exceeded for %s on %s (retry_after=%ds)",
                entity_key,
                self.limit_type,
                retry_after,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many generation requests. Please slow down and try again.",
                headers={"Retry-After": str(retry_after)},
            )

        # 3. Check Supplementary IP Rate Limit
        if self.limit_type == "campaign":
            ip_limit = settings.rate_limit_campaign_ip_per_minute
        else:
            ip_limit = settings.rate_limit_visual_ip_per_minute

        full_ip_key = f"{self.limit_type}:ip:{client_ip}"
        allowed_ip, remaining_ip, retry_after_ip = await store.check_and_increment(
            full_ip_key, ip_limit, window_seconds=60
        )
        if not allowed_ip:
            logger.warning(
                "IP Rate limit exceeded for %s on %s (retry_after=%ds)",
                client_ip,
                self.limit_type,
                retry_after_ip,
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many generation requests from this network. Please try again later.",
                headers={"Retry-After": str(retry_after_ip)},
            )

        return True
