"""CreateX AI - Rate Limiter & Abuse Protection Module

Protects expensive AI generation endpoints against denial of service and quota exhaustion.
Supported Backends:
1. PostgresRateLimitStore:
   - Atomic sliding-log counter in Supabase PostgreSQL via check_rate_limit stored procedure.
   - Zero-cost, 100% atomic across concurrent instances via transaction advisory locks (pg_advisory_xact_lock).
   - FAILS CLOSED with HTTP 503 if database is unavailable.
2. RedisRateLimitStore:
   - Distributed sliding window using Redis sorted sets (when REDIS_URL is configured).
3. InMemoryRateLimitStore:
   - Fast, thread-safe in-memory sliding window for local development and offline unit testing.

Security:
- Identity Strategy:
  * Primary: Authenticated user ID (user:<id>) or validated guest session (guest:<session_id>).
  * Supplementary: Cleaned, validated client IP address (ip:<ip>) to block session-cycling attacks.
  * Untrusted IP headers are sanitized with ipaddress validation.
- HTTP Contract:
  * Returns HTTP 429 Too Many Requests when limits are exceeded, with Retry-After header.
  * Returns HTTP 503 Service Unavailable if the rate-limit store is down (never silently bypasses limits).
"""
import time
import uuid
import asyncio
import logging
import ipaddress
from typing import Optional, Protocol, Tuple
from fastapi import Request, HTTPException, Depends, status

from app.core.config import settings
from app.core.auth import get_current_identity, AuthIdentity

logger = logging.getLogger(__name__)


# ─── STORE EXCEPTIONS & PROTOCOL ─────────────────────────────────────────────

class RateLimitStoreUnavailableError(Exception):
    """Raised when the rate limit storage backend is unavailable or fails."""


class RateLimitStore(Protocol):
    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int]:
        """
        Check if request is permitted under rate limit and record usage.
        Returns:
            (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        Raises:
            RateLimitStoreUnavailableError if store connection fails.
        """
        ...

    async def clear(self) -> None:
        """Clear stored counters (used primarily for test isolation)."""
        ...


# ─── POSTGRESQL ATOMIC RATE LIMIT STORE ───────────────────────────────────────

class PostgresRateLimitStore:
    """
    Atomic sliding-log rate limit store backed by Supabase PostgreSQL.
    Invokes the SECURITY DEFINER function check_rate_limit(p_key, p_max_requests, p_window_secs).
    Uses transaction-level advisory locks to guarantee strict atomicity across concurrent requests.
    FAILS CLOSED with RateLimitStoreUnavailableError if database is unreachable.
    """

    def __init__(self, supabase_client=None):
        self._client = supabase_client

    def _get_client(self):
        if self._client is not None:
            return self._client
        from app.services.supabase_service import get_supabase
        return get_supabase()

    async def check_and_increment(
        self, key: str, max_requests: int, window_seconds: int
    ) -> Tuple[bool, int, int]:
        try:
            client = self._get_client()
            # Execute RPC call in threadpool to prevent blocking the async event loop
            response = await asyncio.to_thread(
                lambda: client.rpc(
                    "check_rate_limit",
                    {
                        "p_key": key,
                        "p_max_requests": max_requests,
                        "p_window_secs": window_seconds,
                    },
                ).execute()
            )

            data = response.data
            if not data or not isinstance(data, list) or len(data) == 0:
                raise ValueError("check_rate_limit stored procedure returned empty response")

            row = data[0]
            allowed = bool(row.get("allowed", False))
            remaining = int(row.get("remaining", 0))
            retry_after = int(row.get("retry_after", 0))
            return allowed, remaining, retry_after

        except Exception as e:
            logger.error("PostgreSQL rate limit store error for key %s: %s", key, e)
            # CRITICAL: Fail closed. Do not silently permit unmetered traffic.
            raise RateLimitStoreUnavailableError(f"PostgreSQL rate limit store unavailable: {e}") from e

    async def clear(self) -> None:
        """Clear all rate limit events from database (for test cleanup)."""
        try:
            client = self._get_client()
            await asyncio.to_thread(
                lambda: client.table("rate_limit_events").delete().neq("id", 0).execute()
            )
        except Exception as e:
            logger.warning("Error clearing rate_limit_events table: %s", e)

    async def cleanup(self, retention_seconds: int = 300, batch_size: int = 5000) -> int:
        """Execute bounded cleanup of expired rate limit events."""
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                lambda: client.rpc(
                    "cleanup_rate_limit_events",
                    {
                        "p_retention_secs": retention_seconds,
                        "p_batch_size": batch_size,
                    },
                ).execute()
            )
            return int(response.data or 0)
        except Exception as e:
            logger.warning("Error running cleanup_rate_limit_events: %s", e)
            return 0


# ─── IN-MEMORY SLIDING-WINDOW STORE ──────────────────────────────────────────

class InMemoryRateLimitStore:
    """Thread-safe sliding-window in-memory store for local development and unit tests."""

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
                # CRITICAL: Do NOT insert timestamp for rejected requests
                return False, 0, retry_after

            timestamps.append(now)
            self._records[key] = timestamps
            remaining = max_requests - len(timestamps)
            return True, remaining, 0

    async def clear(self) -> None:
        async with self._lock:
            self._records.clear()


# ─── REDIS SLIDING-WINDOW STORE ──────────────────────────────────────────────

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
            logger.warning("Redis rate limit error (%s). Falling back to in-memory store.", e)
            return await self._fallback_store.check_and_increment(key, max_requests, window_seconds)

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


# ─── STORE SINGLETON FACTORY ──────────────────────────────────────────────────

_global_store: Optional[RateLimitStore] = None


def get_rate_limit_store() -> RateLimitStore:
    global _global_store
    if _global_store is None:
        store_type = getattr(settings, "rate_limit_store_type", "memory").strip().lower()
        if store_type == "postgres":
            from app.services.supabase_service import is_supabase_configured
            if is_supabase_configured():
                logger.info("Initializing PostgresRateLimitStore backed by Supabase PostgreSQL")
                _global_store = PostgresRateLimitStore()
            else:
                logger.warning("Supabase unconfigured; defaulting to InMemoryRateLimitStore")
                _global_store = InMemoryRateLimitStore()
        elif store_type == "redis" or bool(settings.redis_url):
            logger.info("Initializing RedisRateLimitStore")
            _global_store = RedisRateLimitStore(settings.redis_url)
        else:
            logger.info("Initializing InMemoryRateLimitStore")
            _global_store = InMemoryRateLimitStore()
    return _global_store


def set_rate_limit_store(store: RateLimitStore) -> None:
    """Override rate limit store (used for tests)."""
    global _global_store
    _global_store = store


# ─── FASTAPI DEPENDENCY ───────────────────────────────────────────────────────

def is_trusted_proxy(peer_ip_str: Optional[str], trusted_proxies_config: str) -> bool:
    """
    Check if peer_ip_str belongs to any configured trusted proxy IP or CIDR network.
    Both IPv4 and IPv6 addresses and CIDR notations are supported.
    """
    if not peer_ip_str or not trusted_proxies_config or not trusted_proxies_config.strip():
        return False

    try:
        peer = ipaddress.ip_address(peer_ip_str.strip())
    except ValueError:
        return False

    for item in trusted_proxies_config.split(","):
        entry = item.strip()
        if not entry:
            continue
        try:
            if "/" in entry:
                net = ipaddress.ip_network(entry, strict=False)
                if peer in net:
                    return True
            else:
                trusted_ip = ipaddress.ip_address(entry)
                if peer == trusted_ip:
                    return True
        except ValueError:
            logger.warning("Invalid trusted_proxies configuration entry: %s", entry)
            continue

    return False


class RateLimiter:
    """
    FastAPI dependency that enforces primary (User/Session) and supplementary (IP) rate limits.
    FAILS CLOSED with HTTP 503 if rate limit storage backend is unreachable.
    """

    def __init__(self, limit_type: str):
        self.limit_type = limit_type

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract and validate the effective client IP address.

        Security invariants:
        1. If request.client or request.client.host is missing/invalid, fall back safely to '127.0.0.1'.
        2. Never honor X-Forwarded-For headers unless request.client.host is an explicitly configured trusted proxy.
        3. If upstream peer is not trusted, ignore forwarded headers and use the direct peer address.
        4. If trusted, walk X-Forwarded-For from right to left, stripping trusted proxies to locate the real client IP.
        5. Validate that candidate client IP is a valid IPv4 or IPv6 address.
        6. Handle malformed, empty, and multi-address forwarded headers safely.
        7. Never let a client choose its own trusted-proxy status.
        """
        # 1. Resolve direct socket peer address
        peer_host = None
        if request.client and request.client.host:
            try:
                ipaddress.ip_address(request.client.host.strip())
                peer_host = request.client.host.strip()
            except ValueError:
                pass

        if not peer_host:
            return "127.0.0.1"

        # 2. Check if upstream peer is in configured TRUSTED_PROXIES
        trusted_config = getattr(settings, "trusted_proxies", "")
        if not is_trusted_proxy(peer_host, trusted_config):
            # Peer is not trusted; ignore forwarded headers completely to prevent IP spoofing
            return peer_host

        # 3. Peer is trusted: inspect X-Forwarded-For
        forwarded = request.headers.get("X-Forwarded-For")
        if not forwarded or not forwarded.strip():
            return peer_host

        # Split multiple forwarded addresses: e.g. "client, proxy1, proxy2"
        raw_addrs = [addr.strip() for addr in forwarded.split(",") if addr.strip()]
        if not raw_addrs:
            return peer_host

        # Traverse backwards from right to left (closest proxy to furthest client)
        # Any address matching trusted proxies was added by a trusted intermediate.
        # The first address from the right that is NOT a trusted proxy is the real client.
        for addr in reversed(raw_addrs):
            try:
                candidate = ipaddress.ip_address(addr)
            except ValueError:
                # Malformed entry encountered; ignore invalid entry and continue traversal
                continue

            if not is_trusted_proxy(str(candidate), trusted_config):
                return str(candidate)

        # If all addresses in X-Forwarded-For were themselves trusted proxies, return leftmost valid
        try:
            ipaddress.ip_address(raw_addrs[0])
            return raw_addrs[0]
        except ValueError:
            return peer_host

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
            primary_limit = (
                settings.rate_limit_campaign_auth_per_minute
                if self.limit_type == "campaign"
                else settings.rate_limit_visual_auth_per_minute
            )
        else:
            session_id = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
            if session_id and session_id.strip():
                entity_key = f"guest:{session_id.strip()}"
            else:
                entity_key = f"anon:{client_ip}"

            primary_limit = (
                settings.rate_limit_campaign_per_minute
                if self.limit_type == "campaign"
                else settings.rate_limit_visual_per_minute
            )

        # 2. Check Primary Rate Limit (Fails Closed on Store Failure)
        full_primary_key = f"{self.limit_type}:{entity_key}"
        try:
            allowed, remaining, retry_after = await store.check_and_increment(
                full_primary_key, primary_limit, window_seconds=60
            )
        except RateLimitStoreUnavailableError as e:
            logger.error("Rate limit verification failed closed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting verification service is temporarily unavailable. Please retry.",
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
        ip_limit = (
            settings.rate_limit_campaign_ip_per_minute
            if self.limit_type == "campaign"
            else settings.rate_limit_visual_ip_per_minute
        )

        full_ip_key = f"{self.limit_type}:ip:{client_ip}"
        try:
            allowed_ip, remaining_ip, retry_after_ip = await store.check_and_increment(
                full_ip_key, ip_limit, window_seconds=60
            )
        except RateLimitStoreUnavailableError as e:
            logger.error("IP rate limit verification failed closed: %s", e)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Rate limiting verification service is temporarily unavailable. Please retry.",
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
