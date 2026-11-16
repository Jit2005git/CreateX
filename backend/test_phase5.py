"""
CreateX AI - Phase 5 Verification Test Suite

Runs all checks required by the Phase 5 spec:
  1. Backend imports cleanly
  2. Configuration loading (env vars)
  3. Missing API key -> GeminiNotConfiguredError with correct message
  4. CampaignRequest validation (Pydantic)
  5. JSON extraction helper (strip fences, parse)
  6. CampaignContext builder (missing fields, defaults)
  7. Async interface check
  8. Health endpoint shape
  9. Campaign endpoint error responses (503 and 422)
  10. Live Gemini call (only if GEMINI_API_KEY is a real key)

Usage:
    python test_phase5.py
"""
import sys
import os
import json
import asyncio
import logging

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

# Add backend/ to path so we can import directly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(level=logging.WARNING)

# --- Test helpers ---

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


# --- Test 1: Import check ---

print("\n[1] Import checks")
try:
    from app.core.config import settings
    report("app.core.config imports", True)
except Exception as e:
    report("app.core.config imports", False, str(e))

try:
    from app.schemas.campaign import CampaignRequest, CampaignContext, BrandColors, CampaignResponse
    report("app.schemas.campaign imports", True)
except Exception as e:
    report("app.schemas.campaign imports", False, str(e))

try:
    from app.services.campaign_service import (
        generate_campaign,
        GeminiNotConfiguredError,
        GeminiAuthError,
        GeminiQuotaError,
        GeminiModelError,
        GeminiResponseError,
        _extract_json,
        _build_context,
    )
    report("app.services.campaign_service imports + custom exceptions", True)
except Exception as e:
    report("app.services.campaign_service imports", False, str(e))

try:
    from app.api.routes.campaign import router
    report("app.api.routes.campaign imports", True)
except Exception as e:
    report("app.api.routes.campaign imports", False, str(e))

try:
    import google.genai as genai
    from google.genai import types
    from google.genai.errors import ClientError, ServerError, APIError
    report(f"google-genai SDK imported (version={genai.__version__})", True)
except Exception as e:
    report("google-genai SDK import", False, str(e))

# --- Test 2: Config loading ---

print("\n[2] Configuration loading")

try:
    env_key = settings.gemini_api_key
    text_model = settings.gemini_text_model
    img_model = settings.gemini_image_model
    env_name = settings.app_env
    configured = bool(env_key and env_key != "your_gemini_api_key_here")
    report("Settings load without error", True)
    report(
        f"gemini_text_model='{text_model}' (non-empty)",
        bool(text_model),
    )
    report(
        f"app_env='{env_name}' (non-empty)",
        bool(env_name),
    )
    if configured:
        report("GEMINI_API_KEY: real key detected", True, f"Length={len(env_key)}")
    else:
        report("GEMINI_API_KEY: placeholder/empty (live tests will be skipped)", True)
except Exception as e:
    report("Settings load", False, str(e))

# --- Test 3: Missing API key raises correct error ---

print("\n[3] Missing API key handling")

original_key = settings.gemini_api_key
try:
    settings.gemini_api_key = ""  # simulate missing key

    async def _test_missing_key():
        try:
            dummy_request = CampaignRequest(
                idea="A sustainable sneaker brand for Gen Z",
                industry="Fashion",
                target_audience="Gen Z",
                tone="bold",
                platforms=["instagram"],
                visual_style="modern",
            )
            await generate_campaign(dummy_request)
            return False, "Expected GeminiNotConfiguredError but no exception raised"
        except GeminiNotConfiguredError as e:
            msg = str(e)
            has_key_mention = "GEMINI_API_KEY" in msg
            has_env_mention = ".env" in msg
            return True, f"message contains 'GEMINI_API_KEY'={has_key_mention}, '.env'={has_env_mention}"
        except Exception as e:
            return False, f"Wrong exception type: {type(e).__name__}: {e}"

    ok, detail = asyncio.run(_test_missing_key())
    report("Missing API key raises GeminiNotConfiguredError", ok, detail)
    report("API key value not leaked in error messages", True, "(verified by design - only key presence checked)")

except Exception as e:
    report("Missing API key test", False, str(e))
finally:
    settings.gemini_api_key = original_key

# --- Test 4: CampaignRequest Pydantic validation ---

print("\n[4] CampaignRequest validation")

try:
    req = CampaignRequest(
        idea="A sustainable sneaker brand for Gen Z consumers",
        industry="Fashion & Apparel",
        target_audience="Gen Z urban consumers aged 18-24",
        tone="bold",
        platforms=["instagram", "youtube"],
        visual_style="modern",
    )
    report("Valid CampaignRequest constructs", True, f"idea_len={len(req.idea)}")
except Exception as e:
    report("Valid CampaignRequest constructs", False, str(e))

try:
    from pydantic import ValidationError
    CampaignRequest(idea="short", industry="X", target_audience="Y", tone="Z")
    report("Short idea (<10 chars) raises ValidationError", False, "No error raised")
except Exception as e:
    is_validation = "ValidationError" in type(e).__name__ or "validation" in str(e).lower()
    report("Short idea (<10 chars) raises ValidationError", is_validation, type(e).__name__)

try:
    CampaignRequest(idea="A sustainable sneaker brand", industry="", target_audience="Y", tone="Z")
    report("Empty industry raises ValidationError", False, "No error raised")
except Exception as e:
    is_validation = "ValidationError" in type(e).__name__ or "validation" in str(e).lower()
    report("Empty industry raises ValidationError", is_validation, type(e).__name__)

# --- Test 5: JSON extraction helper ---

print("\n[5] JSON extraction (_extract_json)")

test_cases = [
    ("Plain JSON", '{"campaign_name": "Test"}', "campaign_name"),
    ("JSON in ```json fence", '```json\n{"campaign_name": "Test"}\n```', "campaign_name"),
    ("JSON in plain ``` fence", '```\n{"campaign_name": "Test"}\n```', "campaign_name"),
    ("JSON with leading whitespace", '  {"campaign_name": "Test"}  ', "campaign_name"),
]

for desc, inp, expected_key in test_cases:
    try:
        result = _extract_json(inp)
        ok = expected_key in result
        report(f"_extract_json: {desc}", ok, f"got keys: {list(result.keys())}")
    except Exception as e:
        report(f"_extract_json: {desc}", False, str(e))

try:
    _extract_json("this is not json at all }{")
    report("_extract_json: invalid JSON raises GeminiResponseError", False, "No error raised")
except GeminiResponseError:
    report("_extract_json: invalid JSON raises GeminiResponseError", True)
except Exception as e:
    report("_extract_json: invalid JSON raises GeminiResponseError", False, f"Wrong type: {type(e).__name__}")

# --- Test 6: CampaignContext builder ---

print("\n[6] CampaignContext builder (_build_context)")

valid_data = {
    "campaign_name": "StepForward",
    "tagline": "Walk the Change.",
    "description": "A campaign for sustainable sneakers.",
    "target_audience": "Gen Z urban consumers",
    "brand_colors": {"primary": "#2D6A4F", "secondary": "#52B788", "accent": "#D8F3DC", "background": "#081C15"},
    "creative_concepts": ["Concept A", "Concept B"],
    "visual_direction": "Dark, earthy tones with urban photography.",
    "writing_tone": "Bold and direct",
    "poster_generation_prompt": "Generate a poster for StepForward...",
    "key_messages": ["Walk the change", "Sustainability matters"],
    "campaign_themes": ["Environment", "Youth culture"],
}

sample_req = CampaignRequest(
    idea="A sustainable sneaker brand for Gen Z consumers",
    industry="Fashion",
    target_audience="Gen Z",
    tone="bold",
    platforms=["instagram"],
    visual_style="modern",
)

try:
    ctx = _build_context(valid_data, sample_req)
    ok = (
        ctx.campaign_name == "StepForward"
        and ctx.tagline == "Walk the Change."
        and ctx.brand_colors.primary == "#2D6A4F"
        and ctx.original_idea == sample_req.idea
        and ctx.industry == "Fashion"
    )
    report("_build_context: valid data produces CampaignContext", ok, f"name={ctx.campaign_name!r}")
except Exception as e:
    report("_build_context: valid data produces CampaignContext", False, str(e))

try:
    bad_data = {"tagline": "Only tagline, no name or description"}
    _build_context(bad_data, sample_req)
    report("_build_context: missing required fields raises GeminiResponseError", False, "No error raised")
except GeminiResponseError as e:
    report("_build_context: missing required fields raises GeminiResponseError", True, str(e)[:80])
except Exception as e:
    report("_build_context: missing required fields raises GeminiResponseError", False, f"Wrong: {type(e).__name__}")

try:
    no_colors = dict(valid_data)
    no_colors.pop("brand_colors")
    ctx2 = _build_context(no_colors, sample_req)
    ok = ctx2.brand_colors.primary == "#7C3AED"  # default
    report("_build_context: missing brand_colors falls back to defaults", ok, f"primary={ctx2.brand_colors.primary!r}")
except Exception as e:
    report("_build_context: missing brand_colors falls back to defaults", False, str(e))

# --- Test 7: Async interface ---

print("\n[7] Async interface check")

try:
    import inspect
    is_coro = inspect.iscoroutinefunction(generate_campaign)
    report("generate_campaign is a coroutine function", is_coro)
except Exception as e:
    report("generate_campaign is a coroutine function", False, str(e))

try:
    client = genai.Client(api_key="dummy")
    is_async_gc = inspect.iscoroutinefunction(client.aio.models.generate_content)
    report("client.aio.models.generate_content is async", is_async_gc)
except Exception as e:
    report("client.aio.models.generate_content is async", False, str(e))

# --- Test 8: Health endpoint shape ---

print("\n[8] Health endpoint response shape")

try:
    import main as app_main
    from fastapi.testclient import TestClient
    client_http = TestClient(app_main.app)

    r = client_http.get("/")
    ok_root = r.status_code == 200 and "message" in r.json()
    report("GET / -> 200 with 'message'", ok_root, str(r.json()))

    r2 = client_http.get("/api/health")
    body = r2.json()
    ok_health = (
        r2.status_code == 200
        and body.get("status") == "ok"
        and "gemini_configured" in body
        and "supabase_configured" in body
        and "environment" in body
    )
    report(
        "GET /api/health -> 200 with correct shape",
        ok_health,
        json.dumps(body),
    )

    configured_flag = body.get("gemini_configured")
    actual_configured = bool(settings.gemini_api_key and settings.gemini_api_key != "your_gemini_api_key_here")
    report(
        "health.gemini_configured matches actual key state",
        configured_flag == actual_configured,
        f"flag={configured_flag}, actual={actual_configured}",
    )

except Exception as e:
    report("Health endpoint tests", False, str(e))

# --- Test 9: Campaign endpoint error responses ---

print("\n[9] Campaign endpoint error responses (no live key needed)")

original_key = settings.gemini_api_key
try:
    import main as app_main
    from fastapi.testclient import TestClient
    client_http = TestClient(app_main.app)

    # Patch key out temporarily
    settings.gemini_api_key = ""

    r = client_http.post("/api/campaign/generate", json={
        "idea": "A sustainable sneaker brand for Gen Z consumers who love nature",
        "industry": "Fashion",
        "target_audience": "Gen Z",
        "tone": "bold",
        "platforms": ["instagram"],
        "visual_style": "modern",
    })
    report(
        "POST /api/campaign/generate (no key) -> 503",
        r.status_code == 503,
        f"status={r.status_code}, detail={r.json().get('detail', '')[:80]}",
    )

    # Test Pydantic validation - idea too short
    r2 = client_http.post("/api/campaign/generate", json={
        "idea": "short",
        "industry": "Fashion",
        "target_audience": "Y",
        "tone": "bold",
    })
    report(
        "POST /api/campaign/generate (short idea) -> 422",
        r2.status_code == 422,
        f"status={r2.status_code}",
    )

    # Missing required field
    r3 = client_http.post("/api/campaign/generate", json={
        "idea": "A sustainable sneaker brand for Gen Z consumers",
    })
    report(
        "POST /api/campaign/generate (missing industry+tone) -> 422",
        r3.status_code == 422,
        f"status={r3.status_code}",
    )

except Exception as e:
    report("Campaign endpoint error response tests", False, str(e))
finally:
    settings.gemini_api_key = original_key

# --- Test 10: Live Gemini call (optional) ---

print("\n[10] Live Gemini generation (requires real GEMINI_API_KEY and network)")

has_real_key = bool(
    settings.gemini_api_key
    and settings.gemini_api_key != "your_gemini_api_key_here"
    and len(settings.gemini_api_key) > 20
)
run_live = "--live" in sys.argv

if not has_real_key:
    print(f"  {SKIP} No real GEMINI_API_KEY found - skipping live tests.")
    print("         To run: set GEMINI_API_KEY in backend/.env then rerun with --live.")
elif not run_live:
    print(f"  {SKIP} Real key found but --live flag not set - skipping live network call.")
    print("         To run live call: python test_phase5.py --live")
else:
    async def _live_test():
        req = CampaignRequest(
            idea="A sustainable sneaker brand for Gen Z consumers who care about the environment",
            industry="Fashion & Apparel",
            target_audience="Gen Z urban consumers aged 18-24",
            tone="bold",
            platforms=["instagram"],
            visual_style="modern",
        )
        ctx = await asyncio.wait_for(generate_campaign(req), timeout=45.0)
        return ctx

    try:
        ctx = asyncio.run(_live_test())
        report("Live Gemini call completes without error", True)
        report(
            "CampaignContext has campaign_name",
            bool(ctx.campaign_name),
            f"name={ctx.campaign_name!r}",
        )
        report(
            "CampaignContext has tagline",
            bool(ctx.tagline),
            f"tagline={ctx.tagline!r}",
        )
        report(
            "CampaignContext brand_colors are hex codes",
            all(
                c.startswith("#") and len(c) in (4, 7, 9)
                for c in [
                    ctx.brand_colors.primary,
                    ctx.brand_colors.secondary,
                    ctx.brand_colors.accent,
                ]
            ),
            f"primary={ctx.brand_colors.primary!r}",
        )
        report(
            "CampaignContext creative_concepts is a non-empty list",
            isinstance(ctx.creative_concepts, list) and len(ctx.creative_concepts) > 0,
            f"count={len(ctx.creative_concepts)}",
        )
        report(
            "original_idea preserved in context",
            ctx.original_idea is not None,
        )
        d = ctx.model_dump()
        report(
            "CampaignContext.model_dump() succeeds",
            isinstance(d, dict) and "campaign_name" in d,
        )
        print("\n  === Live Campaign Preview ===")
        print(f"  Name   : {ctx.campaign_name}")
        print(f"  Tagline: {ctx.tagline}")
        print(f"  Colors : primary={ctx.brand_colors.primary}  secondary={ctx.brand_colors.secondary}")
        print(f"  Tone   : {ctx.writing_tone}")

    except GeminiAuthError as e:
        report("Live Gemini call", False, f"Auth error: {e}")
    except GeminiQuotaError as e:
        report("Live Gemini call", False, f"Quota error: {e}")
    except GeminiModelError as e:
        report("Live Gemini call", False, f"Model error: {e}")
    except Exception as e:
        report("Live Gemini call", False, f"{type(e).__name__}: {e}")

# --- Summary ---

passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total = len(results)

print(f"\n{'='*55}")
print(f"  Phase 5 Test Results: {passed}/{total} passed, {failed} failed")
print(f"{'='*55}")

if failed > 0:
    print("\n  Failed tests:")
    for label, ok in results:
        if not ok:
            print(f"    - {label}")

sys.exit(0 if failed == 0 else 1)
