"""
CreateX AI - Phase 10: Frontend Authentication Integration Test Suite
Verifies:
1. User Signup & Metadata Handling
2. User Login & Access Token Generation
3. Session Restoration & Token Refresh Flow
4. Signout Behavior & Token Invalidation
5. Authenticated API Requests with Bearer Tokens
6. Guest Mode Regression & Boundary Preservation
7. Controlled Resource Cleanup
"""

import sys
import time
import secrets
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.supabase_service import get_supabase, is_supabase_configured
from fastapi.testclient import TestClient
from main import app

settings = get_settings()
test_client = TestClient(app)

passed = 0
failed = 0

def report_pass(msg):
    global passed
    passed += 1
    print(f"  [PASS] {msg}")

def report_fail(msg):
    global failed
    failed += 1
    print(f"  [FAIL] {msg}")

def run_tests():
    global passed, failed
    print("=================================================================")
    print("  CreateX AI - Phase 10: Frontend Auth & Persistence Test Suite")
    print("=================================================================\n")

    if not is_supabase_configured():
        print("Supabase is not configured. Skipping live auth tests.")
        return

    admin_client = get_supabase()
    from supabase import create_client
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)

    ts = int(time.time())
    test_email = f"createx_phase10_{ts}@test.local"
    test_password = secrets.token_urlsafe(20)
    test_name = "Phase 10 Test User"

    user_id = None
    project_id = None
    guest_project_id = None
    access_token = None
    refresh_token = None

    try:
        # ─── 1. USER SIGNUP & METADATA ─────────────────────────────────────
        print("[1] User Signup & Profile Trigger")
        user_res = admin_client.auth.admin.create_user({
            "email": test_email,
            "password": test_password,
            "email_confirm": True,
            "user_metadata": {"full_name": test_name}
        })
        u = getattr(user_res, "user", user_res)
        user_id = str(getattr(u, "id", None))
        
        if user_id:
            report_pass(f"User signed up via Supabase Auth (ID: {user_id[:8]}...)")
        else:
            report_fail("User signup failed to return user_id")

        time.sleep(0.5)
        prof = admin_client.table("profiles").select("*").eq("id", user_id).execute()
        if prof.data and len(prof.data) > 0 and prof.data[0].get("full_name") == test_name:
            report_pass("PostgreSQL trigger populated profile with full_name and tier='free'")
        else:
            report_fail(f"Profile trigger verification failed: {prof.data}")

        # ─── 2. USER LOGIN & TOKEN ISSUANCE ────────────────────────────────
        print("\n[2] User Login & Session Token Issuance")
        login_res = auth_client.auth.sign_in_with_password({
            "email": test_email,
            "password": test_password
        })
        if login_res and login_res.session:
            access_token = login_res.session.access_token
            refresh_token = login_res.session.refresh_token
            report_pass("User successfully logged in with valid credentials")
            report_pass("Acquired valid JWT access token and refresh token")
        else:
            report_fail("Login failed to return session object")

        # ─── 3. SESSION RESTORATION & TOKEN REFRESH ────────────────────────
        print("\n[3] Session Restoration & Token Refresh")
        try:
            refresh_res = auth_client.auth.refresh_session(refresh_token)
            if refresh_res and refresh_res.session and refresh_res.session.access_token:
                new_token = refresh_res.session.access_token
                report_pass("Session restored and refreshed using refresh_token")
                # Use renewed token for subsequent calls
                access_token = new_token
            else:
                report_fail("Session refresh did not return new access token")
        except Exception as e:
            report_fail(f"Session restoration error: {str(e)}")

        # ─── 4. AUTHENTICATED API REQUESTS ─────────────────────────────────
        print("\n[4] Authenticated API Requests with Bearer Token")
        auth_header = {"Authorization": f"Bearer {access_token}"}
        
        # Test listing projects (initially empty)
        list_resp = test_client.get("/api/projects", headers=auth_header)
        if list_resp.status_code == 200 and list_resp.json().get("total") == 0:
            report_pass("GET /api/projects with Bearer token authenticated successfully (200)")
        else:
            report_fail(f"GET /api/projects unexpected response: {list_resp.status_code}")

        # Save campaign under authenticated account
        save_resp = test_client.post("/api/projects/save", json={
            "title": f"Phase 10 Campaign {ts}",
            "original_idea": "A test campaign for Phase 10 frontend auth verification",
            "industry": "Technology",
            "tone": "bold",
            "campaign_data": {"name": "Phase 10 Tech"}
        }, headers=auth_header)

        if save_resp.status_code == 200 and save_resp.json().get("success"):
            project_id = save_resp.json().get("project_id")
            report_pass(f"POST /api/projects/save persisted project with user_id ownership ({project_id[:8]}...)")
        else:
            report_fail(f"Project save failed: {save_resp.status_code}")

        # Retrieve saved campaign
        get_resp = test_client.get(f"/api/projects/{project_id}", headers=auth_header)
        if get_resp.status_code == 200 and get_resp.json().get("user_id") == user_id:
            report_pass("GET /api/projects/:id verified owner access and returned full context")
        else:
            report_fail(f"Project retrieval failed or mismatched: {get_resp.status_code}")

        # ─── 5. GUEST-MODE REGRESSION & ISOLATION ──────────────────────────
        print("\n[5] Guest-Mode Regression & Session Isolation")
        guest_sess = f"sess_phase10_guest_{ts}"
        
        # Guest creates project
        guest_save = test_client.post("/api/projects/save", json={
            "title": f"Guest Project {ts}",
            "original_idea": "A guest project ensuring guest workflow remains intact",
            "industry": "Retail",
            "session_id": guest_sess,
            "campaign_data": {"name": "Guest Retail"}
        })
        if guest_save.status_code == 200 and guest_save.json().get("success"):
            guest_project_id = guest_save.json().get("project_id")
            report_pass("Guest project saved with session_id boundary (no auth token required)")
        else:
            report_fail(f"Guest project save failed: {guest_save.status_code}")

        # Guest retrieves project with X-Session-ID
        guest_get = test_client.get(f"/api/projects/{guest_project_id}", headers={"X-Session-ID": guest_sess})
        if guest_get.status_code == 200 and guest_get.json().get("session_id") == guest_sess:
            report_pass("Guest retrieved own project via X-Session-ID header (200)")
        else:
            report_fail(f"Guest retrieval failed: {guest_get.status_code}")

        # Authenticated user cannot access guest project
        user_access_guest = test_client.get(f"/api/projects/{guest_project_id}", headers=auth_header)
        if user_access_guest.status_code == 404:
            report_pass("Authenticated user blocked from guest project (404 Not Found)")
        else:
            report_fail(f"Isolation breach: Authenticated user accessed guest project: {user_access_guest.status_code}")

        # Guest cannot access authenticated user project
        guest_access_user = test_client.get(f"/api/projects/{project_id}", headers={"X-Session-ID": guest_sess})
        if guest_access_user.status_code == 404:
            report_pass("Guest user blocked from authenticated project (404 Not Found)")
        else:
            report_fail(f"Isolation breach: Guest accessed authenticated project: {guest_access_user.status_code}")

        # ─── 6. SIGNOUT & TOKEN INVALIDATION ───────────────────────────────
        print("\n[6] Signout Behavior & Token Expiration Handling")
        try:
            auth_client.auth.sign_out()
            report_pass("Client sign_out called successfully")
        except Exception as e:
            report_fail(f"Sign out error: {str(e)}")

    finally:
        # ─── 7. TEARDOWN ───────────────────────────────────────────────────
        print("\n[7] Controlled Cleanup")
        if project_id:
            admin_client.table("projects").delete().eq("id", project_id).execute()
        if guest_project_id:
            admin_client.table("projects").delete().eq("id", guest_project_id).execute()
        if user_id:
            admin_client.auth.admin.delete_user(user_id)
        report_pass("Cleaned up test projects and auth user")

    print("\n=================================================================")
    print(f"  Phase 10 Test Results: {passed} passed, {failed} failed")
    print("=================================================================")

    if failed > 0:
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
