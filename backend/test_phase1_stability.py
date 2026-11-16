"""
CreateX AI - Phase 1 Verification Test Suite
Tests:
  1. CORS configuration & safety (no wildcard origin with credentials, allowed origins list)
  2. Standardized Error Handling (503 on unconfigured Gemini, 422 on validation, no leaked secrets)
  3. Asset Persistence Architecture:
     - POST /api/projects/{project_id}/assets (save asset)
     - GET /api/projects/{project_id}/assets (list assets)
     - Supabase unconfigured graceful 503 behavior
     - Mock Supabase success path
  4. Storyboard & Social Generation Success Paths with Mocked AI
"""
import sys
import os
import json
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
from app.schemas.campaign import CampaignContext, BrandColors
from app.schemas.project import AssetCreateRequest, AssetSaveResponse, AssetListResponse

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
print("  CreateX AI - Phase 1 Verification Test Suite")
print("=" * 65)


# ----------------------------------------------------------------------
# 1. CORS CONFIGURATION & SECURITY
# ----------------------------------------------------------------------
print("\n[1] CORS Configuration & Security")

# Check that '*' is not in cors_origins
origins = settings.cors_origins
log_test("CORS", "Wildcard '*' origin is strictly prohibited in cors_origins", "*" not in origins, f"origins={origins}")
log_test("CORS", "Frontend URL is included in allowed origins", settings.frontend_url in origins or "http://localhost:5173" in origins)

# Preflight OPTIONS request check
res = client.options(
    "/api/campaign/generate",
    headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    },
)
log_test("CORS", "OPTIONS preflight returns 200 for allowed origin", res.status_code == 200)
log_test(
    "CORS",
    "Access-Control-Allow-Origin header is set and not '*'",
    res.headers.get("access-control-allow-origin") == "http://localhost:5173",
    f"header={res.headers.get('access-control-allow-origin')}",
)


# ----------------------------------------------------------------------
# 2. STANDARDIZED ERROR HANDLING FOR GENERATION ENDPOINTS
# ----------------------------------------------------------------------
print("\n[2] Standardized Error Handling (Unconfigured Gemini Key)")

sample_campaign = {
    "campaign_name": "EcoGlide",
    "tagline": "Glide Through Tomorrow",
    "description": "Next-generation sustainable commuting scooter made from ocean plastic.",
    "original_idea": "Electric scooter with recycled marine plastic frame",
    "industry": "Transportation",
    "target_audience": "Urban commuters aged 22-40",
    "brand_colors": {
        "primary": "#00C9A7",
        "secondary": "#845EC2",
        "accent": "#FF9671",
        "background": "#0B0C10",
    },
    "creative_concepts": ["Clean City Stride", "Ocean to Asphalt"],
    "visual_direction": "Minimalist cyberpunk city dawn with sea-green lighting.",
    "writing_tone": "Optimistic and forward-looking",
    "poster_generation_prompt": "Futuristic electric scooter in front of a modern neon skyline.",
    "key_messages": ["Zero Emissions", "Built from Reclaimed Ocean Materials"],
    "campaign_themes": ["Clean Energy", "Circular Design"],
    "tone": "inspirational",
    "platforms": ["instagram", "youtube"],
    "visual_style": "modern",
}

# Storyboard endpoint without configured Gemini API key -> 503
res_sb_err = client.post(
    "/api/storyboard/generate",
    json={
        "campaign": sample_campaign,
        "video_duration": 30,
        "num_scenes": 4,
        "platform": "instagram",
    },
)
log_test(
    "Error Handling",
    "POST /api/storyboard/generate returns 503 when GEMINI_API_KEY is missing",
    res_sb_err.status_code == 503,
    f"status={res_sb_err.status_code}, detail={res_sb_err.json().get('detail')}",
)

# Social endpoint without configured Gemini API key -> 503
res_soc_err = client.post(
    "/api/social/generate",
    json={
        "campaign": sample_campaign,
        "platforms": ["instagram", "youtube"],
    },
)
log_test(
    "Error Handling",
    "POST /api/social/generate returns 503 when GEMINI_API_KEY is missing",
    res_soc_err.status_code == 503,
    f"status={res_soc_err.status_code}, detail={res_soc_err.json().get('detail')}",
)

# Validation error handling (422)
res_sb_val = client.post(
    "/api/storyboard/generate",
    json={
        "campaign": sample_campaign,
        "video_duration": 10,  # Invalid: ge=15
        "num_scenes": 2,       # Invalid: ge=3
    },
)
log_test("Validation", "POST /api/storyboard/generate rejects out-of-range params with 422", res_sb_val.status_code == 422)

res_soc_val = client.post(
    "/api/social/generate",
    json={},  # Missing campaign
)
log_test("Validation", "POST /api/social/generate rejects empty body with 422", res_soc_val.status_code == 422)


# ----------------------------------------------------------------------
# 3. ASSET PERSISTENCE REST ENDPOINTS
# ----------------------------------------------------------------------
print("\n[3] Asset Persistence Endpoints")

# Unconfigured Supabase -> returns 503 safely
test_proj_id = "11111111-2222-3333-4444-555555555555"

res_asset_unconf = client.post(
    f"/api/projects/{test_proj_id}/assets",
    json={
        "asset_type": "poster",
        "content": {"prompt_used": "EcoGlide visual prompt"},
        "asset_url": "http://localhost:8000/static/posters/poster_123.png",
    },
)
log_test(
    "Asset Persistence",
    "POST /api/projects/:id/assets returns 503 when Supabase is not configured",
    res_asset_unconf.status_code == 503,
    f"status={res_asset_unconf.status_code}",
)

res_list_unconf = client.get(f"/api/projects/{test_proj_id}/assets")
log_test(
    "Asset Persistence",
    "GET /api/projects/:id/assets returns 503 when Supabase is not configured",
    res_list_unconf.status_code == 503,
    f"status={res_list_unconf.status_code}",
)

# Mocked Supabase success path for asset persistence
mock_asset = {
    "id": "asset-uuid-9999",
    "project_id": test_proj_id,
    "asset_type": "poster",
    "content": {"prompt_used": "Test prompt"},
    "asset_url": "http://localhost:8000/static/posters/test.png",
    "created_at": "2026-11-16T20:00:00Z",
}

with patch("app.services.supabase_service.get_project_by_id") as mock_get_proj, \
     patch("app.services.supabase_service.save_asset") as mock_save_asset, \
     patch("app.services.supabase_service.get_assets_for_project") as mock_get_assets:

    mock_get_proj.return_value = {
        "id": test_proj_id,
        "title": "EcoGlide",
        "user_id": "user-9999",
        "session_id": None,
    }
    mock_save_asset.return_value = mock_asset
    mock_get_assets.return_value = [mock_asset]

    user_headers = {"Authorization": "Bearer mock_valid_user_user-9999"}

    # Test POST asset
    res_save_mock = client.post(
        f"/api/projects/{test_proj_id}/assets",
        json={
            "asset_type": "poster",
            "content": {"prompt_used": "Test prompt"},
            "asset_url": "http://localhost:8000/static/posters/test.png",
        },
        headers=user_headers,
    )
    log_test(
        "Asset Persistence",
        "POST /api/projects/:id/assets succeeds (200) with mocked DB",
        res_save_mock.status_code == 200,
        f"status={res_save_mock.status_code}",
    )
    data = res_save_mock.json()
    log_test("Asset Persistence", "Response contains success=True", data.get("success") is True)
    log_test("Asset Persistence", "Response returns correct asset_id", data.get("asset_id") == "asset-uuid-9999")
    log_test("Asset Persistence", "Response associates with project_id", data.get("project_id") == test_proj_id)

    # Test GET assets
    res_get_mock = client.get(f"/api/projects/{test_proj_id}/assets", headers=user_headers)
    log_test(
        "Asset Persistence",
        "GET /api/projects/:id/assets succeeds (200) with mocked DB",
        res_get_mock.status_code == 200,
        f"status={res_get_mock.status_code}",
    )
    list_data = res_get_mock.json()
    log_test("Asset Persistence", "Returns total assets count", list_data.get("total") == 1)
    log_test("Asset Persistence", "Returns matching asset in list", list_data.get("assets", [{}])[0].get("id") == "asset-uuid-9999")


# ----------------------------------------------------------------------
# 4. MOCKED SUCCESS PATH FOR STORYBOARD & SOCIAL
# ----------------------------------------------------------------------
print("\n[4] Mocked AI Generation Success Paths")

mock_sb_json = {
    "video_title": "EcoGlide: Clean City Stride",
    "total_duration": 30,
    "platform": "instagram",
    "scenes": [
        {
            "scene_number": 1,
            "duration_seconds": 10,
            "visual_description": "Commuter riding scooter through morning mist.",
            "camera_direction": "Low angle tracking.",
            "narration": "Cities change when you do.",
            "on_screen_text": "ZERO EMISSIONS",
            "transition": "Quick cut",
            "mood": "Inspiring"
        },
        {
            "scene_number": 2,
            "duration_seconds": 10,
            "visual_description": "Close up of recycled marine plastic frame.",
            "camera_direction": "Macro pan.",
            "narration": "Built from reclaimed ocean materials.",
            "on_screen_text": "CIRCULAR INNOVATION",
            "transition": "Fade",
            "mood": "Focused"
        },
        {
            "scene_number": 3,
            "duration_seconds": 10,
            "visual_description": "Scooter parks at sleek solar charging station.",
            "camera_direction": "Wide static pull out.",
            "narration": "Glide into the future.",
            "on_screen_text": "ECOGLIDE",
            "transition": "Fade to logo",
            "mood": "Empowering"
        }
    ]
}

mock_soc_json = {
    "instagram": {
        "captions": ["Breathe easy. Ride EcoGlide. #UrbanMobility"],
        "hashtags": ["#EcoGlide", "#CleanCommute"],
        "cta": "Link in bio",
        "story_text": "Join the revolution"
    },
    "youtube": {
        "title": "EcoGlide Launch",
        "description": "Meet the sustainable scooter",
        "tags": ["scooter", "electric"],
        "thumbnail_text": "GLIDE",
        "cta": "Subscribe"
    },
    "headlines": ["Clean Commuting Today", "Zero Emissions, Pure Velocity"],
    "ad_copy": "Upgrade your morning commute with EcoGlide."
}

with patch("app.services.storyboard_service.genai.Client") as mock_sb_client:
    m_c = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_sb_json)
    m_c.models.generate_content.return_value = mock_resp
    mock_sb_client.return_value = m_c

    res_sb_success = client.post(
        "/api/storyboard/generate",
        json={
            "campaign": sample_campaign,
            "video_duration": 30,
            "num_scenes": 3,
            "platform": "instagram",
        },
    )
    log_test("Storyboard", "POST /api/storyboard/generate succeeds (200) with mocked AI", res_sb_success.status_code == 200)
    log_test("Storyboard", "Returned storyboard contains scenes", len(res_sb_success.json().get("storyboard", {}).get("scenes", [])) == 3)

with patch("app.services.social_service.genai.Client") as mock_soc_client:
    m_c2 = MagicMock()
    mock_resp2 = MagicMock()
    mock_resp2.text = json.dumps(mock_soc_json)
    m_c2.models.generate_content.return_value = mock_resp2
    mock_soc_client.return_value = m_c2

    res_soc_success = client.post(
        "/api/social/generate",
        json={
            "campaign": sample_campaign,
            "platforms": ["instagram", "youtube"],
        },
    )
    log_test("Social", "POST /api/social/generate succeeds (200) with mocked AI", res_soc_success.status_code == 200)
    log_test("Social", "Returned social contains headlines", len(res_soc_success.json().get("social", {}).get("headlines", [])) == 2)


print("\n" + "=" * 65)
print(f"  Phase 1 Test Results: {results['passed']} passed, {results['failed']} failed")
print("=" * 65)

if results["failed"] > 0:
    sys.exit(1)
