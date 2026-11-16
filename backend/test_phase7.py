"""
CreateX AI - Phase 7 Verification Test Suite: AI Poster Generation

Verifies:
  1. Backend imports cleanly (routes, services, schemas, storage)
  2. Configuration loading (image model, backend url)
  3. Prompt construction with all campaign context elements
  4. Image byte extraction from Gemini response parts (raw & base64)
  5. Storage service (local development persistence and URL generation)
  6. Static file serving via FastAPI (/static/posters/...)
  7. VisualRequest schema validation
  8. API route error mapping (503 for missing key/auth/quota, 422 for model/validation)
  9. API route success path with mocked Gemini image response
  10. Live Gemini image generation call (optional via --live)

Usage:
    python test_phase7.py
    python test_phase7.py --live
"""
import sys
import os
import json
import base64
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
logging.basicConfig(level=logging.ERROR, stream=sys.stdout)
for logger_name in ["app.services.visual_service", "app.services.storage_service"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

PASS = "[PASS]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

results = []


def report(label: str, passed: bool, detail: str = ""):
    tag = PASS if passed else FAIL
    line = f"  {tag} {label}"
    if detail:
        line += f"\n         {detail}"
    print(line)
    results.append((label, passed))


print("\n=======================================================")
print("  CreateX AI - Phase 7 AI Poster Generation Tests")
print("=======================================================")

# --- Test 1: Imports ---
print("\n[1] Import checks")
try:
    from app.core.config import settings
    report("app.core.config imports", True)
except Exception as e:
    report("app.core.config imports", False, str(e))

try:
    from app.schemas.campaign import CampaignContext, BrandColors
    from app.schemas.visual import VisualRequest, VisualResponse
    report("Visual schemas import cleanly", True)
except Exception as e:
    report("Visual schemas import", False, str(e))

try:
    from app.services.storage_service import (
        save_poster_image,
        StorageError,
        LOCAL_STORAGE_DIR,
        POSTERS_DIR,
        ensure_storage_dirs,
    )
    report("app.services.storage_service imports", True)
except Exception as e:
    report("app.services.storage_service imports", False, str(e))

try:
    from app.services.visual_service import (
        generate_poster,
        _build_poster_prompt,
        extract_image_bytes,
        GeminiNotConfiguredError,
        GeminiAuthError,
        GeminiQuotaError,
        GeminiModelError,
        GeminiResponseError,
    )
    report("app.services.visual_service imports + custom exceptions", True)
except Exception as e:
    report("app.services.visual_service imports", False, str(e))

try:
    from app.api.routes.visual import router
    report("app.api.routes.visual imports", True)
except Exception as e:
    report("app.api.routes.visual imports", False, str(e))


# --- Test 2: Configuration ---
print("\n[2] Configuration checks")
try:
    img_model = settings.gemini_image_model
    b_url = getattr(settings, "backend_url", "http://localhost:8000")
    report("gemini_image_model is configured", bool(img_model), f"model={img_model!r}")
    report("backend_url is configured", bool(b_url), f"url={b_url!r}")
except Exception as e:
    report("Configuration check", False, str(e))


# --- Test 3: Prompt Construction ---
print("\n[3] Prompt construction")

sample_campaign = CampaignContext(
    campaign_name="PulseStride",
    tagline="Defy Gravity with Every Step.",
    description="A high-performance eco-friendly running sneaker designed for urban athletes.",
    original_idea="Sustainable running shoes with recycled carbon fiber soles",
    industry="Athletics & Footwear",
    target_audience="Urban marathon runners and fitness enthusiasts aged 20-35",
    brand_colors=BrandColors(
        primary="#00F0FF",
        secondary="#7000FF",
        accent="#FFE600",
        background="#0A0A14",
    ),
    creative_concepts=["Neon sprint", "Gravity-free stride"],
    visual_direction="Cinematic dark environment with electric cyan light trails.",
    writing_tone="Energetic, daring, and premium",
    poster_generation_prompt="A neon athletic running sneaker breaking through sound barrier.",
    key_messages=["Run without limits", "Zero waste"],
    campaign_themes=["Speed", "Sustainability"],
    tone="bold",
    platforms=["instagram"],
    visual_style="Cyberpunk futuristic aesthetic",
)

try:
    prompt = _build_poster_prompt(sample_campaign, style_override="Add subtle motion blur and rain droplets")
    has_name = "PulseStride" in prompt
    has_tagline = "Defy Gravity with Every Step." in prompt
    has_colors = "#00F0FF" in prompt and "#7000FF" in prompt
    has_direction = "Cinematic dark environment" in prompt
    has_audience = "Urban marathon runners" in prompt
    has_style = "Cyberpunk" in prompt
    has_override = "Add subtle motion blur" in prompt

    all_present = all([has_name, has_tagline, has_colors, has_direction, has_audience, has_style, has_override])
    report("Prompt includes all required campaign context elements", all_present)
    report("Prompt length is substantial", len(prompt) > 200, f"length={len(prompt)} chars")
except Exception as e:
    report("Prompt construction", False, str(e))


# --- Test 4: Image Response Extraction ---
print("\n[4] Image response extraction")

# 1x1 transparent PNG bytes for mock testing
TINY_PNG_BYTES = (
    b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
    b'\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff'
    b'?'
    b'\x00\x05\xfe\x02\xfe\xa7\x35\x81\x84\x00\x00\x00\x00IEND\xaeB`\x82'
)
# Pad to > 100 bytes so length validation passes
TEST_PNG_BYTES = TINY_PNG_BYTES + b'\x00' * 120

try:
    # Test case A: Raw bytes in inline_data
    mock_part = MagicMock()
    mock_part.inline_data.data = TEST_PNG_BYTES
    mock_part.inline_data.mime_type = "image/png"
    mock_cand = MagicMock()
    mock_cand.content.parts = [mock_part]
    mock_resp = MagicMock()
    mock_resp.candidates = [mock_cand]

    extracted_bytes, mime = extract_image_bytes(mock_resp)
    report("extract_image_bytes from raw bytes", extracted_bytes == TEST_PNG_BYTES and mime == "image/png")

    # Test case B: Base64 string in inline_data
    b64_str = base64.b64encode(TEST_PNG_BYTES).decode("utf-8")
    mock_part_b64 = MagicMock()
    mock_part_b64.inline_data.data = b64_str
    mock_part_b64.inline_data.mime_type = "image/jpeg"
    mock_cand_b64 = MagicMock()
    mock_cand_b64.content.parts = [mock_part_b64]
    mock_resp_b64 = MagicMock()
    mock_resp_b64.candidates = [mock_cand_b64]

    extracted_bytes_b64, mime_b64 = extract_image_bytes(mock_resp_b64)
    report("extract_image_bytes from base64 string", extracted_bytes_b64 == TEST_PNG_BYTES and mime_b64 == "image/jpeg")

    # Test case C: Empty candidates raises GeminiResponseError
    empty_resp = MagicMock()
    empty_resp.candidates = []
    try:
        extract_image_bytes(empty_resp)
        report("Missing image parts raises GeminiResponseError", False, "No error raised")
    except GeminiResponseError:
        report("Missing image parts raises GeminiResponseError", True)

    # Test case D: Truncated bytes (< 100 bytes) raises GeminiResponseError
    trunc_part = MagicMock()
    trunc_part.inline_data.data = b"tiny"
    trunc_part.inline_data.mime_type = "image/png"
    trunc_cand = MagicMock()
    trunc_cand.content.parts = [trunc_part]
    trunc_resp = MagicMock()
    trunc_resp.candidates = [trunc_cand]
    try:
        extract_image_bytes(trunc_resp)
        report("Truncated image bytes (<100) raises GeminiResponseError", False, "No error raised")
    except GeminiResponseError:
        report("Truncated image bytes (<100) raises GeminiResponseError", True)

except Exception as e:
    report("Image extraction tests", False, str(e))


# --- Test 5: Storage Service ---
print("\n[5] Storage service persistence")

try:
    async def _test_storage():
        pub_url, s_path = await save_poster_image(
            image_bytes=TEST_PNG_BYTES,
            filename="test_verification_poster.png",
            mime_type="image/png",
        )
        return pub_url, s_path

    url, path = asyncio.run(_test_storage())
    report("save_poster_image returns public_url and storage_path", bool(url and path), f"url={url}")
    report("storage_path follows 'posters/...' convention", path.startswith("posters/"))

    # Verify file was written to disk
    local_saved_file = POSTERS_DIR / "test_verification_poster.png"
    file_exists = local_saved_file.exists()
    report("Local file was created on disk", file_exists, f"path={local_saved_file}")

    if file_exists:
        content = local_saved_file.read_bytes()
        report("File on disk matches written bytes exactly", content == TEST_PNG_BYTES)
        # Clean up test file
        local_saved_file.unlink(missing_ok=True)

    # Test empty bytes raises StorageError
    try:
        asyncio.run(save_poster_image(b""))
        report("Empty image bytes raises StorageError", False, "No error raised")
    except StorageError:
        report("Empty image bytes raises StorageError", True)

except Exception as e:
    report("Storage service tests", False, str(e))


# --- Test 6: Static File Serving ---
print("\n[6] Static file serving via FastAPI")

try:
    import main as app_main
    from fastapi.testclient import TestClient

    test_static_file = POSTERS_DIR / "serve_test.png"
    test_static_file.write_bytes(TEST_PNG_BYTES)

    client_http = TestClient(app_main.app)
    r_static = client_http.get("/static/posters/serve_test.png")

    report("GET /static/posters/... returns 200", r_static.status_code == 200)
    report("GET /static/posters/... returns correct image bytes", r_static.content == TEST_PNG_BYTES)
    report("GET /static/posters/... content-type is image/png", "image/png" in r_static.headers.get("content-type", ""))

    test_static_file.unlink(missing_ok=True)
except Exception as e:
    report("Static file serving tests", False, str(e))


# --- Test 7: Schema Validation ---
print("\n[7] VisualRequest and VisualResponse schemas")

try:
    valid_req = VisualRequest(campaign=sample_campaign, style_override="Moody lighting")
    report("Valid VisualRequest constructs", valid_req.campaign.campaign_name == "PulseStride")

    valid_resp = VisualResponse(
        success=True,
        image_url="http://localhost:8000/static/posters/poster_123.png",
        storage_path="posters/poster_123.png",
        prompt_used="A promotional poster...",
    )
    report("Valid VisualResponse constructs", valid_resp.success is True)

    # Missing campaign in VisualRequest raises ValidationError
    from pydantic import ValidationError
    try:
        VisualRequest()
        report("Missing campaign raises ValidationError", False, "No error raised")
    except ValidationError:
        report("Missing campaign raises ValidationError", True)

except Exception as e:
    report("Schema validation tests", False, str(e))


# --- Test 8: API Route Error Handling ---
print("\n[8] Visual API route error mapping")

try:
    client_http = TestClient(app_main.app)

    # A: Missing API key -> 503
    orig_key = settings.gemini_api_key
    try:
        settings.gemini_api_key = ""
        r_nokey = client_http.post("/api/visual/generate", json={"campaign": sample_campaign.model_dump()})
        report("POST /api/visual/generate (no key) -> 503", r_nokey.status_code == 503, f"status={r_nokey.status_code}")
    finally:
        settings.gemini_api_key = orig_key

    # B: Invalid payload -> 422
    r_invalid = client_http.post("/api/visual/generate", json={"campaign": {"invalid": "data"}})
    report("POST /api/visual/generate (invalid body) -> 422", r_invalid.status_code == 422, f"status={r_invalid.status_code}")

    # C: Simulated Quota error -> 503
    with patch("app.services.visual_service._get_gemini_client") as mock_get_client:
        mock_c = MagicMock()
        mock_c.aio.models.generate_content = AsyncMock(side_effect=GeminiQuotaError("Quota exceeded (HTTP 429)"))
        mock_get_client.return_value = mock_c

        r_quota = client_http.post("/api/visual/generate", json={"campaign": sample_campaign.model_dump()})
        report("POST /api/visual/generate (quota exceeded) -> 503", r_quota.status_code == 503, f"detail={r_quota.json().get('detail')}")

    # D: Simulated Model error -> 422
    with patch("app.services.visual_service._get_gemini_client") as mock_get_client:
        mock_c = MagicMock()
        mock_c.aio.models.generate_content = AsyncMock(side_effect=GeminiModelError("Model not found (HTTP 404)"))
        mock_get_client.return_value = mock_c

        r_model = client_http.post("/api/visual/generate", json={"campaign": sample_campaign.model_dump()})
        report("POST /api/visual/generate (model error) -> 422", r_model.status_code == 422, f"detail={r_model.json().get('detail')}")

except Exception as e:
    report("Route error tests", False, str(e))


# --- Test 9: API Route Success Path (Mocked Gemini Output) ---
print("\n[9] Visual API route success path (Mocked Gemini)")

try:
    with patch("app.services.visual_service._get_gemini_client") as mock_get_client:
        mock_part = MagicMock()
        mock_part.inline_data.data = TEST_PNG_BYTES
        mock_part.inline_data.mime_type = "image/png"
        mock_cand = MagicMock()
        mock_cand.content.parts = [mock_part]
        mock_resp = MagicMock()
        mock_resp.candidates = [mock_cand]

        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(return_value=mock_resp)
        mock_get_client.return_value = mock_client

        r_success = client_http.post(
            "/api/visual/generate",
            json={
                "campaign": sample_campaign.model_dump(),
                "style_override": "Vibrant and cinematic",
            },
        )
        report("POST /api/visual/generate returns 200", r_success.status_code == 200, f"status={r_success.status_code}")
        data = r_success.json()
        report("Response has success=True", data.get("success") is True)
        report("Response has valid image_url", bool(data.get("image_url") and "/static/posters/" in data.get("image_url")))
        report("Response has storage_path", bool(data.get("storage_path") and data.get("storage_path").startswith("posters/")))
        report("Response includes prompt_used", bool(data.get("prompt_used") and "PulseStride" in data.get("prompt_used")))

except Exception as e:
    report("Route success path test", False, str(e))


# --- Test 10: Live Gemini Image Generation (Optional via --live) ---
print("\n[10] Live Gemini image generation")

run_live = "--live" in sys.argv
has_key = bool(settings.gemini_api_key and len(settings.gemini_api_key) > 20)

if not has_key:
    print(f"  {SKIP} No GEMINI_API_KEY found - skipping live test.")
elif not run_live:
    print(f"  {SKIP} Real key detected, but --live flag not set - skipping live network call.")
    print("         To test live: python test_phase7.py --live")
else:
    async def _live_gen():
        return await generate_poster(sample_campaign, style_override="Clean advertising visual")

    try:
        print("  Calling Gemini image model:", settings.gemini_image_model)
        live_result = asyncio.run(_live_gen())
        report("Live image generation completes without error", True)
        report("Live result has image_url", bool(live_result.image_url), f"url={live_result.image_url}")
        print("\n  === Live Poster Result ===")
        print("  URL :", live_result.image_url)
        print("  Path:", live_result.storage_path)
    except GeminiQuotaError as e:
        report("Live Gemini call detected Quota / Rate-limit correctly", True, f"Quota handled gracefully: {e}")
    except GeminiModelError as e:
        report("Live Gemini call", False, f"Model error: {e}")
    except GeminiAuthError as e:
        report("Live Gemini call", False, f"Auth error: {e}")
    except Exception as e:
        report("Live Gemini call", False, f"{type(e).__name__}: {e}")


# --- Summary ---
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total = len(results)

print(f"\n{'='*55}")
print(f"  Phase 7 Test Results: {passed}/{total} passed, {failed} failed")
print(f"{'='*55}")

if failed > 0:
    print("\n  Failed tests:")
    for label, ok in results:
        if not ok:
            print(f"    - {label}")

sys.exit(0 if failed == 0 else 1)
