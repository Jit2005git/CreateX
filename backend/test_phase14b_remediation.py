"""CreateX AI - Phase 14B: Production Security Remediation Test Suite

Validates:
1. Authentication Bypass Remediation:
   - Mock tokens fail closed in production (HTTP 401).
   - Mock tokens fail closed when allow_test_tokens is False.
   - Startup validation enforces that allow_test_tokens cannot be enabled in production.
   - Standard dependency overrides work for testing.
   - Valid, invalid, and expired tokens handle correctly without silent guest downgrade.
2. AI Generation Rate Limiting:
   - Requests below limit pass through to generators.
   - Requests exceeding limit receive HTTP 429 with 'Retry-After' header.
   - Primary identity limits for Authenticated Users vs Guest Sessions.
   - Supplementary IP-based rate limiting prevents session-cycling bypass.
   - Rate limiting occurs BEFORE calling expensive AI services (Gemini not invoked on 429).
   - Graceful failover to in-memory store if Redis encounters connection errors.
   - Cross-user and cross-guest quota isolation.
"""
import sys
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from main import app
from app.core.config import settings, Settings
from app.core.auth import get_current_identity, AuthIdentity
from app.core.rate_limiter import (
    InMemoryRateLimitStore,
    RedisRateLimitStore,
    get_rate_limit_store,
    set_rate_limit_store,
)
from app.schemas.campaign import CampaignContext, BrandColors

client = TestClient(app)

results = {"passed": 0, "failed": 0}


def log_test(name: str, passed: bool, detail: str = ""):
    if passed:
        results["passed"] += 1
        print(f"  [PASS] {name}" + (f" -> {detail}" if detail else ""))
    else:
        results["failed"] += 1
        print(f"  [FAIL] {name}" + (f" -> {detail}" if detail else ""))


print("=" * 65)
print("  CreateX AI - Phase 14B Security Remediation Verification Suite")
print("=" * 65)

# Reset store before running
store = InMemoryRateLimitStore()
set_rate_limit_store(store)


# ═════════════════════════════════════════════════════════════════════
# 1. AUTHENTICATION BYPASS REMEDIATION TESTS
# ═════════════════════════════════════════════════════════════════════
print("\n[1] Authentication Bypass Remediation")

# Save original environment state
orig_env = settings.app_env
orig_allow = settings.allow_test_tokens

# A. Production startup safety check
try:
    test_prod_settings = Settings(app_env="production", allow_test_tokens=True)
    test_prod_settings.validate_production_safety()
    log_test("Production Startup Safety Validation", False, "Failed to raise on unsafe production config")
except ValueError as e:
    log_test("Production Startup Safety Validation", True, f"Caught expected invariant error: {e}")

# B. Mock-prefixed token rejected in production
settings.app_env = "production"
settings.allow_test_tokens = False

prod_mock_res = client.get(
    "/api/projects/some-uuid",
    headers={"Authorization": "Bearer mock_valid_user_attacker-uuid-1234"},
)
log_test(
    "Mock Token Rejected in Production (HTTP 401)",
    prod_mock_res.status_code == 401,
    f"status={prod_mock_res.status_code}, detail={prod_mock_res.json().get('detail')}",
)
log_test(
    "WWW-Authenticate Header Present on Production 401",
    prod_mock_res.headers.get("www-authenticate") == "Bearer",
)

# C. Mock-prefixed token rejected in dev if allow_test_tokens is False
settings.app_env = "development"
settings.allow_test_tokens = False

dev_disabled_mock = client.get(
    "/api/projects/some-uuid",
    headers={"Authorization": "Bearer mock_valid_user_test-user"},
)
log_test(
    "Mock Token Rejected in Development when allow_test_tokens=False",
    dev_disabled_mock.status_code == 401,
    f"status={dev_disabled_mock.status_code}",
)

# D. Invalid & Expired Token Rejection (no silent downgrade)
with patch("app.services.supabase_service.is_supabase_configured", return_value=True), \
     patch("app.services.supabase_service.get_supabase") as mock_sb:

    mock_auth = MagicMock()
    mock_auth.get_user.side_effect = Exception("JWT expired or invalid")
    mock_sb.return_value.auth = mock_auth

    expired_res = client.get(
        "/api/projects/some-uuid",
        headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.expired"},
    )
    log_test(
        "Expired Real Token Returns HTTP 401",
        expired_res.status_code == 401,
        f"status={expired_res.status_code}",
    )

    malformed_res = client.get(
        "/api/projects/some-uuid",
        headers={"Authorization": "NotBearer invalid_format"},
    )
    log_test(
        "Malformed Authorization Header Returns HTTP 401",
        malformed_res.status_code == 401,
        f"status={malformed_res.status_code}",
    )

# E. Explicit Test Authentication via Dependency Overrides
dummy_user_id = "test-override-user-7777"
app.dependency_overrides[get_current_identity] = lambda: AuthIdentity(
    user_id=dummy_user_id, email="override@test.local", is_authenticated=True
)

with patch("app.services.supabase_service.get_project_by_id") as mock_proj, \
     patch("app.services.supabase_service.get_assets_for_project", return_value=[]):
    mock_proj.return_value = {
        "id": "proj-7777",
        "user_id": dummy_user_id,
        "title": "Override Project",
        "original_idea": "Test idea",
    }
    override_res = client.get("/api/projects/proj-7777")
    log_test(
        "Explicit Test Authentication via Dependency Overrides Works",
        override_res.status_code == 200,
        f"status={override_res.status_code}",
    )

# Clear override
app.dependency_overrides.pop(get_current_identity, None)

# F. Guest Session Unchanged
with patch("app.services.supabase_service.get_project_by_id") as mock_proj, \
     patch("app.services.supabase_service.get_assets_for_project", return_value=[]):
    mock_proj.return_value = {
        "id": "proj-guest-1",
        "user_id": None,
        "session_id": "sess_valid_guest_111",
        "title": "Guest Project",
        "original_idea": "Guest idea",
    }
    guest_res = client.get(
        "/api/projects/proj-guest-1",
        headers={"X-Session-ID": "sess_valid_guest_111"},
    )
    log_test(
        "Guest Session Verification Unchanged",
        guest_res.status_code == 200,
        f"status={guest_res.status_code}",
    )


# ═════════════════════════════════════════════════════════════════════
# 2. AI GENERATION RATE LIMITING TESTS
# ═════════════════════════════════════════════════════════════════════
print("\n[2] AI Generation Rate Limiting & Abuse Protection")

# Configure rate limit test thresholds
settings.app_env = "development"
settings.rate_limit_enabled = True
settings.rate_limit_campaign_per_minute = 3       # 3 requests for guests
settings.rate_limit_campaign_auth_per_minute = 5  # 5 requests for auth
settings.rate_limit_campaign_ip_per_minute = 10   # 10 requests per IP
settings.rate_limit_visual_per_minute = 2         # 2 requests for guests

test_store = InMemoryRateLimitStore()
set_rate_limit_store(test_store)

mock_campaign_context = CampaignContext(
    campaign_name="Test Campaign",
    tagline="Defy Limits",
    description="A groundbreaking campaign testing rate limits.",
    target_audience="Engineers",
    tone="bold",
    writing_tone="bold and decisive",
    brand_colors=BrandColors(primary="#000000", secondary="#ffffff", accent="#ff0000", background="#111111"),
    creative_concepts=["The Power of Innovation"],
    key_messages=["Speed", "Security"],
    campaign_themes=["Innovation"],
    visual_direction="Modern dark aesthetics",
    poster_generation_prompt="A sleek modern poster",
    original_idea="Test idea",
    industry="Tech",
    platforms=["web"],
)

# Test A: Guest Campaign Generation Rate Limit
gemini_call_count = 0

async def mock_generate_campaign(req):
    global gemini_call_count
    gemini_call_count += 1
    return mock_campaign_context

with patch("app.api.routes.campaign.generate_campaign", side_effect=mock_generate_campaign):
    guest_session = "sess_ratelimit_guest_aaa"
    headers_guest = {"X-Session-ID": guest_session}
    campaign_payload = {
        "idea": "A breakthrough security campaign",
        "industry": "Cybersecurity",
        "target_audience": "DevOps",
        "tone": "bold",
        "platforms": ["twitter"],
        "visual_style": "minimal",
    }

    # Request 1: Allowed
    r1 = client.post("/api/campaign/generate", json=campaign_payload, headers=headers_guest)
    log_test("Guest Campaign Request 1 (Within Limit)", r1.status_code == 200, f"status={r1.status_code}")

    # Request 2: Allowed
    r2 = client.post("/api/campaign/generate", json=campaign_payload, headers=headers_guest)
    log_test("Guest Campaign Request 2 (Within Limit)", r2.status_code == 200, f"status={r2.status_code}")

    # Request 3: Allowed
    r3 = client.post("/api/campaign/generate", json=campaign_payload, headers=headers_guest)
    log_test("Guest Campaign Request 3 (Reaches Limit)", r3.status_code == 200, f"status={r3.status_code}")

    # Request 4: Exceeded -> 429
    r4 = client.post("/api/campaign/generate", json=campaign_payload, headers=headers_guest)
    log_test(
        "Guest Campaign Request 4 (Exceeds Limit -> HTTP 429)",
        r4.status_code == 429,
        f"status={r4.status_code}, detail={r4.json().get('detail')}",
    )
    log_test(
        "Retry-After Header Present on 429",
        "retry-after" in r4.headers and int(r4.headers.get("retry-after")) > 0,
        f"Retry-After={r4.headers.get('retry-after')}s",
    )
    log_test(
        "AI Provider NOT Invoked on 429 (Protected Before Compute)",
        gemini_call_count == 3,
        f"calls={gemini_call_count} (expected exactly 3)",
    )

# Test B: Guest Session Isolation (Guest Bob is NOT blocked by Guest Alice's limit)
with patch("app.api.routes.campaign.generate_campaign", side_effect=mock_generate_campaign):
    guest_bob_session = "sess_ratelimit_guest_bob"
    r_bob = client.post(
        "/api/campaign/generate",
        json=campaign_payload,
        headers={"X-Session-ID": guest_bob_session},
    )
    log_test(
        "Guest Session Isolation (Separate Guest Bob Allowed Under Alice Limit)",
        r_bob.status_code == 200,
        f"status={r_bob.status_code}",
    )

# Test C: Authenticated User Limit & Isolation
with patch("app.api.routes.campaign.generate_campaign", side_effect=mock_generate_campaign):
    # Configure user 1 override
    app.dependency_overrides[get_current_identity] = lambda: AuthIdentity(
        user_id="user-auth-limit-1", email="user1@limit.test", is_authenticated=True
    )

    # User 1 limit is 5 requests
    u1_statuses = []
    for _ in range(5):
        res = client.post("/api/campaign/generate", json=campaign_payload)
        u1_statuses.append(res.status_code)

    u1_exceeded = client.post("/api/campaign/generate", json=campaign_payload)
    log_test(
        "Authenticated User Limit Enforced (5 Allowed, 6th Blocked with 429)",
        all(s == 200 for s in u1_statuses) and u1_exceeded.status_code == 429,
        f"statuses={u1_statuses} -> 6th={u1_exceeded.status_code}",
    )

    # User 2 override (User 2 should still have fresh quota)
    app.dependency_overrides[get_current_identity] = lambda: AuthIdentity(
        user_id="user-auth-limit-2", email="user2@limit.test", is_authenticated=True
    )
    u2_res = client.post("/api/campaign/generate", json=campaign_payload)
    log_test(
        "Authenticated User Isolation (User 2 Has Independent Quota)",
        u2_res.status_code == 200,
        f"status={u2_res.status_code}",
    )

    app.dependency_overrides.pop(get_current_identity, None)

# Test D: Supplementary IP-based protection prevents session cycling bypass
with patch("app.api.routes.campaign.generate_campaign", side_effect=mock_generate_campaign):
    # An attacker creates a new session ID for every request, but from the same IP
    attacker_ip = "198.51.100.42"
    ip_headers = {"X-Forwarded-For": attacker_ip}

    # IP limit is 10 requests per minute
    ip_statuses = []
    for i in range(10):
        res = client.post(
            "/api/campaign/generate",
            json=campaign_payload,
            headers={"X-Forwarded-For": attacker_ip, "X-Session-ID": f"cycled_session_{i}"},
        )
        ip_statuses.append(res.status_code)

    # 11th request from same IP with yet another session ID
    ip_blocked = client.post(
        "/api/campaign/generate",
        json=campaign_payload,
        headers={"X-Forwarded-For": attacker_ip, "X-Session-ID": "cycled_session_999"},
    )
    log_test(
        "Supplementary IP Limit Blocks Session Cycling Attack (HTTP 429)",
        ip_blocked.status_code == 429 and "network" in ip_blocked.json().get("detail", ""),
        f"status={ip_blocked.status_code}, detail={ip_blocked.json().get('detail')}",
    )

# Test E: Visual / Poster Rate Limit
from app.schemas.visual import VisualResponse

async def mock_generate_poster(campaign, style):
    return VisualResponse(
        success=True,
        image_url="https://test.supabase.co/storage/v1/object/public/createx-posters/posters/test.png",
        storage_path="posters/test.png",
        prompt_used="test prompt",
    )

with patch("app.api.routes.visual.generate_poster", side_effect=mock_generate_poster):
    visual_session = "sess_visual_limit_test"
    visual_payload = {"campaign": mock_campaign_context.model_dump(), "style_override": None}

    # Limit is 2 for guests
    v1 = client.post("/api/visual/generate", json=visual_payload, headers={"X-Session-ID": visual_session})
    v2 = client.post("/api/visual/generate", json=visual_payload, headers={"X-Session-ID": visual_session})
    v3 = client.post("/api/visual/generate", json=visual_payload, headers={"X-Session-ID": visual_session})

    log_test(
        "Visual Generation Separate Limit (2 Allowed, 3rd Blocked with 429)",
        v1.status_code == 200 and v2.status_code == 200 and v3.status_code == 429,
        f"v1={v1.status_code}, v2={v2.status_code}, v3={v3.status_code}",
    )


# ═════════════════════════════════════════════════════════════════════
# 3. DISTRIBUTED REDIS STORE & FAILSAFE BEHAVIOR
# ═════════════════════════════════════════════════════════════════════
print("\n[3] Distributed Redis Store & Failsafe Resilience")

async def test_redis_store_and_fallback():
    class MockPipeline:
        def __init__(self, execute_res):
            self.execute_res = execute_res

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        def zremrangebyscore(self, *args, **kwargs):
            pass

        def zcard(self, *args, **kwargs):
            pass

        def zrange(self, *args, **kwargs):
            pass

        def zadd(self, *args, **kwargs):
            pass

        def expire(self, *args, **kwargs):
            pass

        async def execute(self):
            return self.execute_res

    class MockRedisClient:
        def __init__(self):
            self.execute_res = [0, 0, []]

        def pipeline(self, transaction=True):
            return MockPipeline(self.execute_res)

    # A. Test Mocked Redis Store (Within Limit)
    mock_client = MockRedisClient()
    mock_client.execute_res = [0, 0, []]

    redis_store = RedisRateLimitStore("redis://localhost:6379/0")
    redis_store._redis = mock_client

    allowed, rem, retry = await redis_store.check_and_increment("test_key", 5, 60)
    log_test(
        "Redis Sliding Window Query Executes Pipeline",
        allowed is True and rem == 4,
        f"allowed={allowed}, remaining={rem}",
    )

    # B. Test Redis Exceeded State
    earliest_time = time.time() - 30  # 30 seconds ago
    mock_client.execute_res = [0, 5, [("entry_1", earliest_time)]]
    allowed_exc, rem_exc, retry_exc = await redis_store.check_and_increment("test_key", 5, 60)
    log_test(
        "Redis Rate Limit Exceeded Calculation",
        allowed_exc is False and 28 <= retry_exc <= 32,
        f"allowed={allowed_exc}, retry_after={retry_exc}s",
    )

    # C. Test Redis Failure Graceful Fallback to In-Memory Store
    class FailingRedisClient:
        def pipeline(self, transaction=True):
            raise Exception("Redis connection refused: ECONNREFUSED")

    redis_store._redis = FailingRedisClient()

    # Should not raise; falls back safely to in-memory store
    fallback_allowed, fallback_rem, _ = await redis_store.check_and_increment("fallback_key", 2, 60)
    log_test(
        "Redis Outage Graceful Fallback to In-Memory Store",
        fallback_allowed is True and fallback_rem == 1,
        f"allowed={fallback_allowed}, remaining={fallback_rem}",
    )

asyncio.run(test_redis_store_and_fallback())

# Restore environment settings
settings.app_env = orig_env
settings.allow_test_tokens = orig_allow
settings.rate_limit_campaign_per_minute = 5
settings.rate_limit_campaign_auth_per_minute = 15
settings.rate_limit_campaign_ip_per_minute = 25
settings.rate_limit_visual_per_minute = 3
set_rate_limit_store(InMemoryRateLimitStore())

print("\n" + "=" * 65)
print(f"  Phase 14B Results: {results['passed']} passed, {results['failed']} failed")
print("=" * 65)

if results["failed"] > 0:
    sys.exit(1)
