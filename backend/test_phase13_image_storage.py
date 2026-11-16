"""
CreateX AI - Phase 13: Real Image Storage & Retrieval Verification Suite
Verifies:
1. Upload of valid PNG, JPEG, and WebP images to live 'createx-posters' Supabase bucket.
2. Direct Storage object inspection & metadata recording in 'generated_assets'.
3. Retrieval via Storage SDK and public CDN URL; byte-for-byte & SHA-256 checksum comparison.
4. Ownership, cross-user isolation, and guest-session isolation on image assets.
5. Error handling: invalid MIME types, oversized payloads (>10MB), empty files, non-existent projects, invalid tokens.
6. Clean teardown of all storage objects, database rows, and test users.
"""

import sys
import time
import secrets
import hashlib
import urllib.request
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.services.supabase_service import get_supabase, is_supabase_configured
from app.services.storage_service import save_poster_image, StorageError
from fastapi.testclient import TestClient
from main import app

settings = get_settings()
test_client = TestClient(app)

results = {
    "scenarios": {},
    "cleanup_log": [],
    "summary": {"pass": 0, "fail": 0},
}

def log_result(scenario, name, status, details=""):
    if scenario not in results["scenarios"]:
        results["scenarios"][scenario] = []
    results["scenarios"][scenario].append({"name": name, "status": status, "details": details})
    if status == "PASS":
        results["summary"]["pass"] += 1
        print(f"  [{status}] {name} - {details}")
    else:
        results["summary"]["fail"] += 1
        print(f"  [{status}] {name} - {details}")

# Real valid 1x1 test images
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00"
    b"\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7V\xfe\xae\x00\x00\x00\x00IEND\xaeB`\x82"
)
TINY_JPEG = (
    b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00\x08\x06"
    b"\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d"
    b"\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\xff\xc0\x00\x0b\x08\x00"
    b"\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00"
    b"\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00"
    b"\x00?\x00\xbf\x00\xff\xd9"
)
TINY_WEBP = (
    b"RIFF\x1a\x00\x00\x00WEBPVP8L\x0e\x00\x00\x00/\x00\x00\x00\x00\x07\x88\x81\x00\x04P\x00\x00"
)

async def run_tests():
    print("=================================================================")
    print("  CreateX AI - Phase 13: Real Image Storage & Retrieval Verification")
    print("=================================================================\n")

    if not is_supabase_configured():
        print("FAIL: Supabase is not configured. Aborting live test.")
        sys.exit(1)

    admin_client = get_supabase()
    from supabase import create_client
    auth_client = create_client(settings.supabase_url, settings.supabase_anon_key)

    bucket_name = settings.supabase_storage_bucket or "createx-posters"
    ts = int(time.time())

    # State tracking for clean teardown
    tracked_storage_paths = []
    tracked_project_ids = []
    tracked_user_ids = []

    try:
        # ═════════════════════════════════════════════════════════════════
        # SCENARIO A: AUTHENTICATED USER UPLOAD, RETRIEVAL & INTEGRITY
        # ═════════════════════════════════════════════════════════════════
        print("[Scenario A] Authenticated User Image Storage & Integrity")
        u1_email = f"phase13_user1_{ts}@test.local"
        u1_pwd = secrets.token_urlsafe(20)

        # 1. Create User 1 & sign in
        u1_res = admin_client.auth.admin.create_user({
            "email": u1_email,
            "password": u1_pwd,
            "email_confirm": True,
            "user_metadata": {"full_name": "Phase 13 User 1"}
        })
        u1_id = str(getattr(u1_res, "user", u1_res).id)
        tracked_user_ids.append(u1_id)

        login_res = auth_client.auth.sign_in_with_password({"email": u1_email, "password": u1_pwd})
        u1_token = login_res.session.access_token
        auth_header_u1 = {"Authorization": f"Bearer {u1_token}"}

        # 2. Create campaign project
        p1_save = test_client.post("/api/projects/save", json={
            "title": f"Phase 13 Project {ts}",
            "original_idea": "Real image upload verification project",
            "industry": "Technology",
            "tone": "bold",
            "campaign_data": {"name": "Image Storage Campaign"}
        }, headers=auth_header_u1)
        p1_id = p1_save.json()["project_id"]
        tracked_project_ids.append(p1_id)
        log_result("Scenario A", "Create Authenticated Project", "PASS", f"Project created: {p1_id[:8]}...")

        # 3. Upload real PNG image to Supabase Storage
        png_sha256 = hashlib.sha256(TINY_PNG).hexdigest()
        png_filename = f"test_poster_{ts}.png"
        public_url, storage_path = await save_poster_image(
            image_bytes=TINY_PNG,
            filename=png_filename,
            mime_type="image/png"
        )
        tracked_storage_paths.append(storage_path)
        log_result("Scenario A", "Upload Real PNG to Supabase Storage", "PASS", f"Stored at {storage_path}")

        # 4. Record metadata in generated_assets via API
        asset_save_resp = test_client.post(
            f"/api/projects/{p1_id}/assets",
            json={
                "asset_type": "poster",
                "content": {"headline": "Visual Poster Test", "dimensions": "1x1"},
                "asset_url": public_url,
                "storage_path": storage_path,
            },
            headers=auth_header_u1
        )
        a1_id = asset_save_resp.json()["asset_id"]
        log_result("Scenario A", "Record Asset Metadata in Database", "PASS", f"Asset recorded: {a1_id[:8]}... with storage_path={storage_path}")

        # 5. Verify direct Storage object exists & download bytes via SDK
        downloaded_bytes = admin_client.storage.from_(bucket_name).download(storage_path)
        downloaded_sha256 = hashlib.sha256(downloaded_bytes).hexdigest()
        bytes_match = (downloaded_bytes == TINY_PNG)
        checksum_match = (downloaded_sha256 == png_sha256)

        if bytes_match and checksum_match:
            log_result("Scenario A", "SDK Image Download & Checksum Verification", "PASS", f"Byte length: {len(downloaded_bytes)}, SHA256 match: {png_sha256[:12]}...")
        else:
            log_result("Scenario A", "SDK Image Download & Checksum Verification", "FAIL", f"Checksum mismatch: {downloaded_sha256} vs {png_sha256}")

        # 6. Verify Public CDN URL retrieval via HTTP GET
        req = urllib.request.Request(public_url, headers={"User-Agent": "CreateX-Verification/1.0"})
        with urllib.request.urlopen(req) as response:
            cdn_bytes = response.read()
            cdn_content_type = response.headers.get("Content-Type")
            cdn_sha256 = hashlib.sha256(cdn_bytes).hexdigest()

        if cdn_bytes == TINY_PNG and "png" in cdn_content_type.lower():
            log_result("Scenario A", "Public CDN URL Direct Retrieval", "PASS", f"Retrieved {len(cdn_bytes)} bytes over CDN (Content-Type: {cdn_content_type})")
        else:
            log_result("Scenario A", "Public CDN URL Direct Retrieval", "FAIL", f"CDN bytes mismatch or wrong Content-Type: {cdn_content_type}")

        # 7. Test JPEG and WebP upload formats
        jpeg_url, jpeg_path = await save_poster_image(TINY_JPEG, filename=f"test_poster_{ts}.jpg", mime_type="image/jpeg")
        tracked_storage_paths.append(jpeg_path)
        jpeg_download = admin_client.storage.from_(bucket_name).download(jpeg_path)
        if jpeg_download == TINY_JPEG:
            log_result("Scenario A", "JPEG Upload & Exact Byte Retrieval", "PASS", f"JPEG {len(TINY_JPEG)} bytes verified")
        else:
            log_result("Scenario A", "JPEG Upload & Exact Byte Retrieval", "FAIL", "JPEG byte mismatch")

        webp_url, webp_path = await save_poster_image(TINY_WEBP, filename=f"test_poster_{ts}.webp", mime_type="image/webp")
        tracked_storage_paths.append(webp_path)
        webp_download = admin_client.storage.from_(bucket_name).download(webp_path)
        if webp_download == TINY_WEBP:
            log_result("Scenario A", "WebP Upload & Exact Byte Retrieval", "PASS", f"WebP {len(TINY_WEBP)} bytes verified")
        else:
            log_result("Scenario A", "WebP Upload & Exact Byte Retrieval", "FAIL", "WebP byte mismatch")

        # 8. Refresh Workspace / Project Reload Verification
        reload_resp = test_client.get(f"/api/projects/{p1_id}", headers=auth_header_u1)
        r_data = reload_resp.json()
        r_assets = r_data.get("assets", [])
        matching_asset = next((a for a in r_assets if a.get("id") == a1_id), None)
        if matching_asset and matching_asset.get("storage_path") == storage_path and matching_asset.get("asset_url") == public_url:
            log_result("Scenario A", "Workspace Reload Asset Metadata Persistence", "PASS", "Asset storage_path and asset_url retained on project reload")
        else:
            log_result("Scenario A", "Workspace Reload Asset Metadata Persistence", "FAIL", f"Reload mismatch: {matching_asset}")


        # ═════════════════════════════════════════════════════════════════
        # SCENARIO B: GUEST SESSION IMAGE STORAGE & ISOLATION
        # ═════════════════════════════════════════════════════════════════
        print("\n[Scenario B] Guest Session Image Storage & Isolation")
        guest_alice_session = f"sess_guest_alice_{ts}"
        guest_bob_session = f"sess_guest_bob_{ts}"

        # 1. Guest Alice creates campaign
        alice_proj_resp = test_client.post("/api/projects/save", json={
            "title": f"Alice Guest Project {ts}",
            "original_idea": "Guest campaign for poster testing",
            "session_id": guest_alice_session,
            "campaign_data": {"name": "Alice Guest Campaign"}
        })
        alice_pid = alice_proj_resp.json()["project_id"]
        tracked_project_ids.append(alice_pid)

        # 2. Upload guest poster
        alice_img_url, alice_img_path = await save_poster_image(
            TINY_PNG,
            filename=f"alice_guest_{ts}.png",
            mime_type="image/png"
        )
        tracked_storage_paths.append(alice_img_path)

        # 3. Save asset to Alice's project using X-Session-ID
        alice_asset_resp = test_client.post(
            f"/api/projects/{alice_pid}/assets",
            json={
                "asset_type": "poster",
                "content": {"headline": "Alice Poster"},
                "asset_url": alice_img_url,
                "storage_path": alice_img_path,
            },
            headers={"X-Session-ID": guest_alice_session}
        )
        alice_aid = alice_asset_resp.json()["asset_id"]
        log_result("Scenario B", "Guest Asset Creation with Session Boundary", "PASS", f"Alice asset saved: {alice_aid[:8]}...")

        # 4. Alice retrieves her assets
        alice_list = test_client.get(f"/api/projects/{alice_pid}/assets", headers={"X-Session-ID": guest_alice_session})
        if alice_list.status_code == 200 and alice_list.json()["total"] == 1:
            log_result("Scenario B", "Guest Asset Retrieval by Authorized Session", "PASS", "Alice retrieved own assets (200 OK)")
        else:
            log_result("Scenario B", "Guest Asset Retrieval by Authorized Session", "FAIL", f"Status: {alice_list.status_code}")

        # 5. Guest Bob attempts to access Alice's assets -> 404
        bob_get_assets = test_client.get(f"/api/projects/{alice_pid}/assets", headers={"X-Session-ID": guest_bob_session})
        bob_del_project = test_client.delete(f"/api/projects/{alice_pid}", headers={"X-Session-ID": guest_bob_session})
        if bob_get_assets.status_code == 404 and bob_del_project.status_code == 404:
            log_result("Scenario B", "Guest Session Boundary Enforcement", "PASS", "Guest Bob blocked from listing (404) or deleting (404) Alice's project & assets")
        else:
            log_result("Scenario B", "Guest Session Boundary Enforcement", "FAIL", f"Breach! GET={bob_get_assets.status_code}, DEL={bob_del_project.status_code}")


        # ═════════════════════════════════════════════════════════════════
        # SCENARIO C: CROSS-USER ISOLATION ON STORED ASSETS
        # ═════════════════════════════════════════════════════════════════
        print("\n[Scenario C] Cross-User Isolation on Stored Assets")
        u2_email = f"phase13_user2_{ts}@test.local"
        u2_pwd = secrets.token_urlsafe(20)

        # Create User 2
        u2_res = admin_client.auth.admin.create_user({
            "email": u2_email,
            "password": u2_pwd,
            "email_confirm": True,
            "user_metadata": {"full_name": "Phase 13 User 2"}
        })
        u2_id = str(getattr(u2_res, "user", u2_res).id)
        tracked_user_ids.append(u2_id)

        login_u2 = auth_client.auth.sign_in_with_password({"email": u2_email, "password": u2_pwd})
        u2_token = login_u2.session.access_token
        auth_header_u2 = {"Authorization": f"Bearer {u2_token}"}

        # User 2 attempts to read User 1's assets -> 404
        u2_get_assets = test_client.get(f"/api/projects/{p1_id}/assets", headers=auth_header_u2)
        # User 2 attempts to append an asset to User 1's project -> 404
        u2_post_asset = test_client.post(
            f"/api/projects/{p1_id}/assets",
            json={"asset_type": "poster", "content": {"headline": "Attacker Poster"}},
            headers=auth_header_u2
        )
        # User 2 attempts to delete User 1's project -> 404
        u2_del_proj = test_client.delete(f"/api/projects/{p1_id}", headers=auth_header_u2)

        if u2_get_assets.status_code == 404 and u2_post_asset.status_code == 404 and u2_del_proj.status_code == 404:
            log_result("Scenario C", "Cross-User Asset & Project Protection", "PASS", "User 2 cannot list assets (404), attach asset (404), or delete project (404)")
        else:
            log_result("Scenario C", "Cross-User Asset & Project Protection", "FAIL", f"Breach! GET={u2_get_assets.status_code}, POST={u2_post_asset.status_code}, DEL={u2_del_proj.status_code}")


        # ═════════════════════════════════════════════════════════════════
        # SCENARIO D: ERROR HANDLING & EDGE CASES
        # ═════════════════════════════════════════════════════════════════
        print("\n[Scenario D] Error Handling & Edge Cases")

        # 1. Empty image bytes
        try:
            await save_poster_image(b"", filename="empty.png")
            log_result("Scenario D", "Empty Image Bytes Rejection", "FAIL", "Empty bytes did not raise StorageError")
        except StorageError:
            log_result("Scenario D", "Empty Image Bytes Rejection", "PASS", "Empty image bytes rejected with StorageError")

        # 2. Invalid MIME type upload to Supabase Storage
        # Storage bucket policy restricts allowed_mime_types to ['image/png', 'image/jpeg', 'image/webp']
        try:
            admin_client.storage.from_(bucket_name).upload(
                path=f"posters/malicious_{ts}.exe",
                file=b"MZ\x90\x00executable_code_here",
                file_options={"content-type": "application/x-executable", "upsert": "true"}
            )
            # If upload did not raise, check if file was rejected
            log_result("Scenario D", "Disallowed MIME Type Rejection", "FAIL", "Storage permitted non-image MIME type upload")
        except Exception as e:
            log_result("Scenario D", "Disallowed MIME Type Rejection", "PASS", f"Rejected by Storage bucket policy: {type(e).__name__}")

        # 3. Oversized file (>10 MB limit)
        # 10.5 MB dummy byte array
        oversized_bytes = b"0" * (10485760 + 512000)
        try:
            admin_client.storage.from_(bucket_name).upload(
                path=f"posters/oversized_{ts}.png",
                file=oversized_bytes,
                file_options={"content-type": "image/png", "upsert": "true"}
            )
            log_result("Scenario D", "Oversized File (>10MB) Rejection", "FAIL", "Storage permitted >10MB upload")
        except Exception as e:
            log_result("Scenario D", "Oversized File (>10MB) Rejection", "PASS", f"Rejected by Storage 10MB limit: {type(e).__name__}")

        # 4. Invalid / non-existent project reference
        fake_pid = "00000000-0000-0000-0000-000000000000"
        fake_asset_resp = test_client.post(
            f"/api/projects/{fake_pid}/assets",
            json={"asset_type": "poster", "content": {"test": "orphan"}},
            headers=auth_header_u1
        )
        if fake_asset_resp.status_code == 404:
            log_result("Scenario D", "Non-Existent Project Reference", "PASS", "Asset attach rejected with 404 Project not found")
        else:
            log_result("Scenario D", "Non-Existent Project Reference", "FAIL", f"Unexpected status {fake_asset_resp.status_code}")

        # 5. Invalid / malformed Bearer token
        bad_token_resp = test_client.post(
            f"/api/projects/{p1_id}/assets",
            json={"asset_type": "poster", "content": {"test": "bad_token"}},
            headers={"Authorization": "Bearer malformed_expired_token_12345"}
        )
        if bad_token_resp.status_code == 401:
            log_result("Scenario D", "Invalid Bearer Token Rejection", "PASS", "Rejected with 401 Unauthorized")
        else:
            log_result("Scenario D", "Invalid Bearer Token Rejection", "FAIL", f"Unexpected status {bad_token_resp.status_code}")

    finally:
        # ═════════════════════════════════════════════════════════════════
        # CONTROLLED TEARDOWN & CLEANUP
        # ═════════════════════════════════════════════════════════════════
        print("\n[Cleanup] Controlled Teardown of Test Resources")
        
        # 1. Remove storage objects from bucket
        if tracked_storage_paths:
            try:
                admin_client.storage.from_(bucket_name).remove(tracked_storage_paths)
                for p in tracked_storage_paths:
                    results["cleanup_log"].append(f"Deleted storage object: {p}")
            except Exception as e:
                results["cleanup_log"].append(f"Error deleting storage objects: {str(e)}")

        # 2. Delete projects (cascades generated_assets)
        for pid in tracked_project_ids:
            try:
                admin_client.table("projects").delete().eq("id", pid).execute()
                results["cleanup_log"].append(f"Deleted project: {pid}")
            except Exception as e:
                results["cleanup_log"].append(f"Error deleting project {pid}: {str(e)}")

        # 3. Delete temporary auth users (cascades profiles)
        for uid in tracked_user_ids:
            try:
                admin_client.auth.admin.delete_user(uid)
                results["cleanup_log"].append(f"Deleted auth user: {uid}")
            except Exception as e:
                results["cleanup_log"].append(f"Error deleting user {uid}: {str(e)}")

        # 4. Verify zero leftovers
        time.sleep(0.5)
        leftover_projs = admin_client.table("projects").select("id").in_("id", tracked_project_ids).execute()
        leftover_users = admin_client.table("profiles").select("id").in_("id", tracked_user_ids).execute()
        
        if len(leftover_projs.data or []) == 0 and len(leftover_users.data or []) == 0:
            print("  [PASS] Teardown Verified: Zero leftover database records or test users.")
        else:
            print("  [FAIL] Teardown Warning: Leftover records detected.")

    print("\n=================================================================")
    print(f"  Phase 13 Summary: {results['summary']['pass']} passed, {results['summary']['fail']} failed")
    print("=================================================================")

    if results["summary"]["fail"] > 0:
        sys.exit(1)

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_tests()) if hasattr(asyncio, "run") else None
