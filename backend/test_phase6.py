"""
CreateX AI - Phase 6 Regression Test Suite: Storyboard & Social Media Generation

Verifies:
  1. Storyboard schemas (StoryboardRequest, Scene, StoryboardData, StoryboardResponse)
  2. Social media schemas (SocialRequest, InstagramContent, YouTubeContent, SocialContent, SocialResponse)
  3. Storyboard prompt construction and JSON parsing
  4. Social media prompt construction and JSON parsing
  5. Storyboard API route (POST /api/storyboard/generate)
  6. Social API route (POST /api/social/generate)
  7. Live generation with Gemini text model (optional via --live)

Usage:
    python test_phase6.py
    python test_phase6.py --live
"""
import sys
import os
import json
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
print("  CreateX AI - Phase 6 Storyboard & Social Tests")
print("=======================================================")

# --- Test 1: Imports ---
print("\n[1] Import checks")
try:
    from app.schemas.campaign import CampaignContext, BrandColors
    from app.schemas.storyboard import StoryboardRequest, StoryboardResponse, StoryboardData, Scene
    from app.schemas.social import SocialRequest, SocialResponse, SocialData, InstagramContent, YouTubeContent
    report("Storyboard & Social schemas import cleanly", True)
except Exception as e:
    report("Schemas import", False, str(e))

try:
    from app.services.storyboard_service import generate_storyboard
    from app.services.social_service import generate_social
    report("Storyboard & Social services import cleanly", True)
except Exception as e:
    report("Services import", False, str(e))

try:
    from app.api.routes import storyboard, social
    report("Storyboard & Social routes import cleanly", True)
except Exception as e:
    report("Routes import", False, str(e))


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
    platforms=["instagram", "youtube"],
    visual_style="Cyberpunk futuristic aesthetic",
)


# --- Test 2: Storyboard Validation & Service Mock ---
print("\n[2] Storyboard schema & service")
try:
    s_req = StoryboardRequest(
        campaign=sample_campaign,
        video_duration=30,
        num_scenes=4,
        platform="youtube",
    )
    report("Valid StoryboardRequest constructs", s_req.video_duration == 30)

    mock_storyboard_json = {
        "video_title": "PulseStride: Defy Gravity",
        "total_duration": 30,
        "platform": "youtube",
        "scenes": [
            {
                "scene_number": 1,
                "duration_seconds": 6,
                "visual_description": "Close-up of runner tying recycled carbon fiber laces.",
                "camera_direction": "Macro low-angle tracking shot.",
                "narration": "What if your stride left nothing behind but momentum?",
                "on_screen_text": "ZERO FOOTPRINT",
                "transition": "Quick whip-pan to city streets",
                "mood": "Anticipatory and determined"
            },
            {
                "scene_number": 2,
                "duration_seconds": 8,
                "visual_description": "Runner sprints across neon wet asphalt, light reflections underfoot.",
                "camera_direction": "Side tracking tracking at sprint speed.",
                "narration": "Engineered for pure velocity. Crafted from circular innovation.",
                "on_screen_text": "DEFY GRAVITY",
                "transition": "Hard cut to mid-stride freeze",
                "mood": "High energy"
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.text = json.dumps(mock_storyboard_json)

    with patch("app.services.storyboard_service.genai.Client") as mock_client_cls:
        mock_c = MagicMock()
        mock_c.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_c

        sb_result = asyncio.run(generate_storyboard(s_req))
        report("generate_storyboard parses valid StoryboardData", isinstance(sb_result, StoryboardData))
        report("StoryboardData has expected video_title", sb_result.video_title == "PulseStride: Defy Gravity")
        report("StoryboardData has correct number of scenes", len(sb_result.scenes) == 2)
        report("First scene has valid visual_description", bool(sb_result.scenes[0].visual_description))

except Exception as e:
    report("Storyboard service test", False, str(e))


# --- Test 3: Social Media Validation & Service Mock ---
print("\n[3] Social media schema & service")
try:
    soc_req = SocialRequest(
        campaign=sample_campaign,
        platforms=["instagram", "youtube"],
    )
    report("Valid SocialRequest constructs", "instagram" in soc_req.platforms)

    mock_social_json = {
        "instagram": {
            "captions": [
                "Lace up. Step forward. Defy gravity. ⚡ #PulseStride",
                "What if sustainability and speed were the same thing? 🏃‍♂️",
                "Built from circular innovation for runners who refuse limits."
            ],
            "hashtags": ["#PulseStride", "#SustainableRunning", "#EcoSneakers", "#RunWild", "#UrbanAthletes"],
            "cta": "Tap the link in bio to join the drop.",
            "story_text": "Tomorrow morning. 08:00 AM."
        },
        "youtube": {
            "title": "PulseStride: Defy Gravity | Official Launch Film",
            "description": "Meet PulseStride. High-performance recycled carbon fiber running sneakers.",
            "tags": ["running shoes", "sustainable sneakers", "PulseStride", "marathon training"],
            "thumbnail_text": "DEFY GRAVITY",
            "cta": "Subscribe for early access."
        },
        "headlines": [
            "Defy Gravity with Every Step",
            "The Future of Sustainable Velocity",
            "Zero Waste. Pure Momentum."
        ],
        "ad_copy": "Engineered for speed, crafted for the planet. Experience PulseStride today."
    }

    mock_resp_soc = MagicMock()
    mock_resp_soc.text = json.dumps(mock_social_json)

    with patch("app.services.social_service.genai.Client") as mock_client_cls:
        mock_c = MagicMock()
        mock_c.models.generate_content.return_value = mock_resp_soc
        mock_client_cls.return_value = mock_c

        soc_result = asyncio.run(generate_social(soc_req))
        report("generate_social parses valid SocialData", isinstance(soc_result, SocialData))
        report("SocialData contains 3 Instagram captions", len(soc_result.instagram.captions) == 3)
        report("SocialData contains YouTube metadata", bool(soc_result.youtube.title))
        report("SocialData contains promotional headlines", len(soc_result.headlines) == 3)

except Exception as e:
    report("Social service test", False, str(e))


# --- Test 4: API Routes via TestClient ---
print("\n[4] API route endpoints")
try:
    import main as app_main
    from fastapi.testclient import TestClient

    client_http = TestClient(app_main.app)

    # Test POST /api/storyboard/generate
    with patch("app.services.storyboard_service.genai.Client") as mock_client_cls:
        mock_c = MagicMock()
        mock_c.models.generate_content.return_value = mock_resp
        mock_client_cls.return_value = mock_c

        r_sb = client_http.post(
            "/api/storyboard/generate",
            json={
                "campaign": sample_campaign.model_dump(),
                "video_duration": 30,
                "num_scenes": 3,
                "platform": "youtube",
            },
        )
        report("POST /api/storyboard/generate returns 200", r_sb.status_code == 200, f"status={r_sb.status_code}")
        report("Storyboard response has success=True", r_sb.json().get("success") is True)

    # Test POST /api/social/generate
    with patch("app.services.social_service.genai.Client") as mock_client_cls:
        mock_c = MagicMock()
        mock_c.models.generate_content.return_value = mock_resp_soc
        mock_client_cls.return_value = mock_c

        r_soc = client_http.post(
            "/api/social/generate",
            json={
                "campaign": sample_campaign.model_dump(),
                "platforms": ["instagram", "youtube"],
            },
        )
        report("POST /api/social/generate returns 200", r_soc.status_code == 200, f"status={r_soc.status_code}")
        report("Social response has success=True", r_soc.json().get("success") is True)

except Exception as e:
    report("API route tests", False, str(e))


# --- Test 5: Live Generation (Optional via --live) ---
print("\n[5] Live generation check")
run_live = "--live" in sys.argv
if not run_live:
    print(f"  {SKIP} Pass --live to run live Gemini API calls for Storyboard & Social.")
else:
    async def _live_phase6():
        sb = await generate_storyboard(s_req)
        soc = await generate_social(soc_req)
        return sb, soc

    try:
        sb, soc = asyncio.run(_live_phase6())
        report("Live Storyboard generation succeeds", len(sb.scenes) > 0, f"scenes={len(sb.scenes)}")
        report("Live Social generation succeeds", len(soc.instagram.captions) > 0, f"captions={len(soc.instagram.captions)}")
    except Exception as e:
        report("Live generation", False, str(e))


# --- Summary ---
passed = sum(1 for _, ok in results if ok)
failed = sum(1 for _, ok in results if not ok)
total = len(results)

print(f"\n{'='*55}")
print(f"  Phase 6 Test Results: {passed}/{total} passed, {failed} failed")
print(f"{'='*55}")

if failed > 0:
    print("\n  Failed tests:")
    for label, ok in results:
        if not ok:
            print(f"    - {label}")

sys.exit(0 if failed == 0 else 1)
