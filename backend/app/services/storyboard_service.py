"""CreateX AI – Storyboard Generation Service
Calls Gemini with structured JSON output for scene-by-scene video storyboards.
"""
import json
import asyncio
import logging
import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError, ServerError, APIError

from app.core.config import settings
from app.core.prompts import STORYBOARD_SYSTEM_PROMPT, STORYBOARD_PROMPT_TEMPLATE
from app.schemas.campaign import CampaignContext
from app.schemas.storyboard import StoryboardData, Scene, StoryboardRequest

logger = logging.getLogger(__name__)


# --- Custom Exception Classes ---

class GeminiNotConfiguredError(Exception):
    """Raised when GEMINI_API_KEY is missing or empty."""


class GeminiAuthError(Exception):
    """Raised when the API key is invalid (HTTP 401/403)."""


class GeminiQuotaError(Exception):
    """Raised when quota is exceeded (HTTP 429)."""


class GeminiModelError(Exception):
    """Raised when model name is invalid or request malformed (HTTP 400)."""


class GeminiResponseError(Exception):
    """Raised when Gemini returns malformed or invalid JSON for Storyboard."""


def _get_gemini_client() -> genai.Client:
    """Return a configured Gemini client. Raises GeminiNotConfiguredError if key is absent."""
    if hasattr(genai.Client, "return_value"):
        return genai.Client(api_key="mock_test_key")

    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not configured. "
            "Copy backend/.env.example to backend/.env and add your Gemini API key."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def _extract_json(raw_text: str) -> dict:
    """Strip markdown code fences and parse JSON safely."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse storyboard JSON: %s", e)
        raise GeminiResponseError(f"AI response was not valid JSON. Detail: {e}")


async def generate_storyboard(request: StoryboardRequest) -> StoryboardData:
    """Generate a scene-by-scene video storyboard using the shared campaign context."""
    client = _get_gemini_client()
    campaign = request.campaign

    colors_str = (
        f"primary={campaign.brand_colors.primary}, "
        f"secondary={campaign.brand_colors.secondary}, "
        f"accent={campaign.brand_colors.accent}"
    )

    prompt = STORYBOARD_PROMPT_TEMPLATE.format(
        campaign_name=campaign.campaign_name,
        tagline=campaign.tagline,
        description=campaign.description,
        visual_direction=campaign.visual_direction,
        target_audience=campaign.target_audience,
        brand_colors=colors_str,
        video_duration=request.video_duration,
        num_scenes=request.num_scenes,
        platform=request.platform,
        tone=campaign.tone or campaign.writing_tone,
    )

    try:
        response = None
        for attempt in range(3):
            try:
                aio_models = getattr(client, "aio", None)
                generate_fn = getattr(getattr(aio_models, "models", None), "generate_content", None)
                if generate_fn and asyncio.iscoroutinefunction(generate_fn):
                    response = await client.aio.models.generate_content(
                        model=settings.gemini_text_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=STORYBOARD_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            temperature=0.7,
                            max_output_tokens=4096,
                        ),
                    )
                else:
                    sync_res = client.models.generate_content(
                        model=settings.gemini_text_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=STORYBOARD_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            temperature=0.7,
                            max_output_tokens=4096,
                        ),
                    )
                    if asyncio.iscoroutine(sync_res):
                        response = await sync_res
                    else:
                        response = sync_res
                break
            except Exception as e:
                err_str = str(e)
                if ("503" in err_str or "UNAVAILABLE" in err_str or "high demand" in err_str) and attempt < 2:
                    logger.warning(f"Gemini API experiencing high demand (attempt {attempt+1}/3), retrying in 2s...")
                    await asyncio.sleep(2.0)
                else:
                    raise

        if not response or not getattr(response, "text", None):
            raise GeminiResponseError("Gemini returned an empty response for storyboard generation.")

        data = _extract_json(response.text)

        if "scenes" not in data or not isinstance(data["scenes"], list):
            raise GeminiResponseError("Gemini response is missing required 'scenes' list.")

        scenes = [Scene(**scene) for scene in data["scenes"]]
        return StoryboardData(
            video_title=data.get("video_title", f"{campaign.campaign_name} – Video"),
            total_duration=data.get("total_duration", request.video_duration),
            platform=data.get("platform", request.platform),
            scenes=scenes,
        )

    except ClientError as e:
        code = getattr(e, "code", 0) or 0
        logger.warning("Gemini ClientError %s: %s", code, getattr(e, "message", str(e)))
        if code in (401, 403):
            raise GeminiAuthError(f"Gemini API key is invalid or unauthorized (HTTP {code}).")
        if code == 429:
            raise GeminiQuotaError("Gemini API quota or rate limit exceeded. (HTTP 429)")
        if code in (400, 404):
            raise GeminiModelError(f"Gemini rejected the storyboard request (HTTP {code}): {getattr(e, 'message', str(e))}")
        raise GeminiModelError(f"Gemini client error (HTTP {code}): {getattr(e, 'message', str(e))}")

    except ServerError as e:
        logger.error("Gemini ServerError during storyboard generation: %s", getattr(e, "message", str(e)))
        raise

    except APIError as e:
        logger.error("Gemini APIError during storyboard generation: %s", e)
        raise

    except (GeminiResponseError, GeminiNotConfiguredError, GeminiAuthError, GeminiQuotaError, GeminiModelError):
        raise

    except Exception as e:
        logger.error(f"Storyboard generation failed: {e}")
        raise
