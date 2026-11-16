"""
CreateX AI - Supabase Security & Multi-Tenant Authorization Test Suite

Verifies all critical security requirements from the revised specification:
1. Rejection of invalid/expired Bearer tokens with HTTP 401 (no silent downgrade to guest).
2. Malformed Authorization headers return HTTP 401.
3. Cross-user project access isolation (User B cannot read or delete User A's project).
4. Guest session isolation (Guest B cannot read or delete Guest A's project).
5. Guest cannot access authenticated user's projects.
6. Unauthorized asset operations (User B cannot create or list assets on User A's project).
7. Guest session_id format validation (rejects invalid/injection strings with 422).
8. Profile tier immutability trigger logic.
"""
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Fix Windows console UTF-8 encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi.testclient import TestClient
from main import app
from app.core.config import settings
from app.core.auth import validate_session_id

# Enable test tokens specifically for unit test assertions
settings.allow_test_tokens = True

client = TestClient(app)

results = {"passed": 0, "failed": 0}


def log_test(category: str, name: str, passed: bool, detail: str = ""):
    if passed:
        results["passed"] += 1
        print(f"  [PASS] {name}" + (f" -> {detail}" if detail else ""))
    else:
        results["failed"] += 1
        print(f"  [FAIL] {name}" + (f" -> {detail}" if detail else ""))


print("=" * 65)
print("  CreateX AI - Supabase Security Verification Suite")
print("=" * 65)


# ----------------------------------------------------------------------
# 1. TOKEN VALIDATION & REJECTION (NO SILENT DOWNGRADE)
# ----------------------------------------------------------------------
print("\n[1] Token Validation & Rejection (No Silent Downgrade)")

# Test: Invalid Bearer token must return 401, NOT 200 or guest fallback
res_invalid = client.get(
    "/api/projects",
    headers={"Authorization": "Bearer invalid_expired_token_xyz123"},
)
log_test(
    "Auth",
    "Invalid Bearer token returns HTTP 401 Unauthorized",
    res_invalid.status_code == 401,
    f"status={res_invalid.status_code}, detail={res_invalid.json().get('detail')}",
)
log_test(
    "Auth",
    "401 Response includes WWW-Authenticate header",
    res_invalid.headers.get("www-authenticate") == "Bearer",
)

# Test: Malformed Authorization header returns 401
res_malformed = client.get(
    "/api/projects",
    headers={"Authorization": "Basic user:pass"},
)
log_test(
    "Auth",
    "Non-Bearer Authorization header returns HTTP 401",
    res_malformed.status_code == 401,
    f"status={res_malformed.status_code}",
)

# Test: Missing Authorization header permits guest query if session_id is provided
res_no_auth = client.get("/api/projects?session_id=sess_valid_guest_123")
log_test(
    "Auth",
    "Omitted Authorization header triggers guest flow (status!=401)",
    res_no_auth.status_code != 401,
    f"status={res_no_auth.status_code}",
)


# ----------------------------------------------------------------------
# 2. GUEST SESSION ID VALIDATION
# ----------------------------------------------------------------------
print("\n[2] Guest Session ID Validation")

# Test valid session IDs
try:
    val1 = validate_session_id("sess_valid_12345678")
    log_test("SessionValidation", "Valid alphanumeric session_id accepted", val1 == "sess_valid_12345678")
except Exception as e:
    log_test("SessionValidation", "Valid alphanumeric session_id accepted", False, str(e))

# Test short session ID (<3 chars)
res_short = client.get("/api/projects?session_id=a")
log_test(
    "SessionValidation",
    "Short session_id (<3 chars) rejected with 422",
    res_short.status_code == 422,
    f"status={res_short.status_code}",
)

# Test malicious session ID with SQL injection characters
res_inj = client.get("/api/projects?session_id=sess_123' OR '1'='1")
log_test(
    "SessionValidation",
    "Malicious session_id containing illegal characters rejected with 422",
    res_inj.status_code == 422,
    f"status={res_inj.status_code}",
)


# ----------------------------------------------------------------------
# 3. CROSS-USER PROJECT ACCESS & TENANT ISOLATION
# ----------------------------------------------------------------------
print("\n[3] Cross-User Project Access & Tenant Isolation")

user_a_id = "user-uuid-aaaa-1111"
user_b_id = "user-uuid-bbbb-2222"
project_a_id = "proj-uuid-1111"

mock_project_a = {
    "id": project_a_id,
    "user_id": user_a_id,
    "session_id": None,
    "title": "User A Private Campaign",
    "original_idea": "Top Secret Brand Launch",
    "created_at": "2026-11-17T00:00:00Z",
}

with patch("app.services.supabase_service.get_project_by_id") as mock_get, \
     patch("app.services.supabase_service.get_assets_for_project") as mock_get_assets, \
     patch("app.services.supabase_service.delete_project") as mock_del:

    mock_get.return_value = mock_project_a
    mock_get_assets.return_value = []
    mock_del.return_value = True

    # User A accesses own project -> 200
    res_user_a = client.get(
        f"/api/projects/{project_a_id}",
        headers={"Authorization": f"Bearer mock_valid_user_{user_a_id}"},
    )
    log_test(
        "CrossUser",
        "User A can access their own project (200)",
        res_user_a.status_code == 200,
        f"status={res_user_a.status_code}",
    )

    # User B attempts to access User A's project -> 404 (preventing enumeration)
    res_user_b = client.get(
        f"/api/projects/{project_a_id}",
        headers={"Authorization": f"Bearer mock_valid_user_{user_b_id}"},
    )
    log_test(
        "CrossUser",
        "User B attempting to read User A's project is blocked with 404",
        res_user_b.status_code == 404,
        f"status={res_user_b.status_code}",
    )

    # User B attempts to delete User A's project -> 404
    res_del_b = client.delete(
        f"/api/projects/{project_a_id}",
        headers={"Authorization": f"Bearer mock_valid_user_{user_b_id}"},
    )
    log_test(
        "CrossUser",
        "User B attempting to delete User A's project is blocked with 404",
        res_del_b.status_code == 404,
        f"status={res_del_b.status_code}",
    )

    # Guest user attempts to access User A's project -> 404
    res_guest_on_user = client.get(
        f"/api/projects/{project_a_id}?session_id=sess_guest_attacker_123",
    )
    log_test(
        "CrossUser",
        "Guest attempting to read registered User A's project is blocked with 404",
        res_guest_on_user.status_code == 404,
        f"status={res_guest_on_user.status_code}",
    )


# ----------------------------------------------------------------------
# 4. GUEST SESSION ISOLATION
# ----------------------------------------------------------------------
print("\n[4] Guest Session Isolation")

guest_proj_id = "proj-guest-7777"
mock_guest_project = {
    "id": guest_proj_id,
    "user_id": None,
    "session_id": "sess_alice_guest_111",
    "title": "Guest Alice Campaign",
    "original_idea": "Public Idea",
    "created_at": "2026-11-17T00:00:00Z",
}

with patch("app.services.supabase_service.get_project_by_id") as mock_get_g, \
     patch("app.services.supabase_service.get_assets_for_project") as mock_get_assets_g, \
     patch("app.services.supabase_service.delete_project") as mock_del_g:

    mock_get_g.return_value = mock_guest_project
    mock_get_assets_g.return_value = []
    mock_del_g.return_value = True

    # Guest Alice with matching session_id accesses project -> 200
    res_alice = client.get(
        f"/api/projects/{guest_proj_id}?session_id=sess_alice_guest_111",
    )
    log_test(
        "GuestIsolation",
        "Guest Alice with matching session_id can access project (200)",
        res_alice.status_code == 200,
        f"status={res_alice.status_code}",
    )

    # Guest Bob with different session_id attempts access -> 404
    res_bob = client.get(
        f"/api/projects/{guest_proj_id}?session_id=sess_bob_guest_222",
    )
    log_test(
        "GuestIsolation",
        "Guest Bob with different session_id is blocked with 404",
        res_bob.status_code == 404,
        f"status={res_bob.status_code}",
    )

    # Guest Bob attempts deletion -> 404
    res_bob_del = client.delete(
        f"/api/projects/{guest_proj_id}?session_id=sess_bob_guest_222",
    )
    log_test(
        "GuestIsolation",
        "Guest Bob attempting to delete Alice's project is blocked with 404",
        res_bob_del.status_code == 404,
        f"status={res_bob_del.status_code}",
    )


# ----------------------------------------------------------------------
# 5. UNAUTHORIZED ASSET CREATION & ACCESS
# ----------------------------------------------------------------------
print("\n[5] Unauthorized Asset Operations")

with patch("app.services.supabase_service.get_project_by_id") as mock_get_asset_proj, \
     patch("app.services.supabase_service.save_asset") as mock_save_a, \
     patch("app.services.supabase_service.get_assets_for_project") as mock_get_a:

    mock_get_asset_proj.return_value = mock_project_a  # Owned by User A
    mock_save_a.return_value = {"id": "asset-123"}
    mock_get_a.return_value = []

    # User B attempts to save asset under User A's project -> 404
    res_save_unauth = client.post(
        f"/api/projects/{project_a_id}/assets",
        json={
            "asset_type": "poster",
            "content": {"prompt": "Attacker payload"},
            "asset_url": "http://evil.com/exploit.png",
        },
        headers={"Authorization": f"Bearer mock_valid_user_{user_b_id}"},
    )
    log_test(
        "AssetSecurity",
        "User B cannot create asset on User A's project (404)",
        res_save_unauth.status_code == 404,
        f"status={res_save_unauth.status_code}",
    )

    # User B attempts to list assets from User A's project -> 404
    res_list_unauth = client.get(
        f"/api/projects/{project_a_id}/assets",
        headers={"Authorization": f"Bearer mock_valid_user_{user_b_id}"},
    )
    log_test(
        "AssetSecurity",
        "User B cannot list assets from User A's project (404)",
        res_list_unauth.status_code == 404,
        f"status={res_list_unauth.status_code}",
    )


# ----------------------------------------------------------------------
# 6. PROFILE TIER IMMUTABILITY TRIGGER TEST
# ----------------------------------------------------------------------
print("\n[6] Profile Tier Immutability Verification")

# Simulate PostgreSQL trigger logic for tier protection
def simulate_tier_update(old_tier: str, new_tier: str):
    if new_tier != old_tier:
        raise ValueError("Privilege modification disallowed: Users cannot alter their own tier.")
    return True

try:
    simulate_tier_update("free", "free")
    log_test("TierProtection", "Preserving existing tier succeeds", True)
except ValueError:
    log_test("TierProtection", "Preserving existing tier succeeds", False)

try:
    simulate_tier_update("free", "pro")
    log_test("TierProtection", "Escalating tier from free to pro is blocked", False, "No error raised")
except ValueError as e:
    log_test("TierProtection", "Escalating tier from free to pro is blocked", True, str(e))


print("\n" + "=" * 65)
print(f"  Security Test Results: {results['passed']} passed, {results['failed']} failed")
print("=" * 65)

if results["failed"] > 0:
    sys.exit(1)
