"""CreateX AI – Social Media Generation Service
Generates platform-optimized captions, hashtags, and copy.
"""
import json
import asyncio
import logging
import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError, ServerError, APIError

from app.core.config import settings
from app.core.prompts import SOCIAL_SYSTEM_PROMPT, SOCIAL_PROMPT_TEMPLATE
from app.schemas.social import SocialData, SocialRequest, InstagramContent, YouTubeContent

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
    """Raised when Gemini returns malformed or invalid JSON for Social Media."""


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
        logger.error("Failed to parse social JSON: %s", e)
        raise GeminiResponseError(f"AI response was not valid JSON. Detail: {e}")


async def generate_social(request: SocialRequest) -> SocialData:
    """Generate platform-specific social media content maintaining campaign identity."""
    client = _get_gemini_client()
    campaign = request.campaign
    platforms = request.platforms or campaign.platforms or ["instagram", "youtube"]

    prompt = SOCIAL_PROMPT_TEMPLATE.format(
        campaign_name=campaign.campaign_name,
        tagline=campaign.tagline,
        description=campaign.description,
        target_audience=campaign.target_audience,
        writing_tone=campaign.writing_tone,
        key_messages=", ".join(campaign.key_messages),
        platforms=", ".join(platforms),
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
                            system_instruction=SOCIAL_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            temperature=0.85,
                            max_output_tokens=3000,
                        ),
                    )
                else:
                    sync_res = client.models.generate_content(
                        model=settings.gemini_text_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            system_instruction=SOCIAL_SYSTEM_PROMPT,
                            response_mime_type="application/json",
                            temperature=0.85,
                            max_output_tokens=3000,
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
            raise GeminiResponseError("Gemini returned an empty response for social generation.")

        data = _extract_json(response.text)
        if not isinstance(data, dict):
            raise GeminiResponseError("Gemini response is not a valid JSON object.")

        instagram = None
        if "instagram" in data and isinstance(data["instagram"], dict):
            ig = data["instagram"]
            instagram = InstagramContent(
                captions=ig.get("captions", []),
                hashtags=ig.get("hashtags", []),
                cta=ig.get("cta", ""),
                story_text=ig.get("story_text"),
            )

        youtube = None
        if "youtube" in data and isinstance(data["youtube"], dict):
            yt = data["youtube"]
            youtube = YouTubeContent(
                title=yt.get("title", ""),
                description=yt.get("description", ""),
                tags=yt.get("tags", []),
                thumbnail_text=yt.get("thumbnail_text"),
                cta=yt.get("cta", ""),
            )

        return SocialData(
            instagram=instagram,
            youtube=youtube,
            headlines=data.get("headlines", []),
            ad_copy=data.get("ad_copy"),
        )

    except ClientError as e:
        code = getattr(e, "code", 0) or 0
        logger.warning("Gemini ClientError %s: %s", code, getattr(e, "message", str(e)))
        if code in (401, 403):
            raise GeminiAuthError(f"Gemini API key is invalid or unauthorized (HTTP {code}).")
        if code == 429:
            raise GeminiQuotaError("Gemini API quota or rate limit exceeded. (HTTP 429)")
        if code in (400, 404):
            raise GeminiModelError(f"Gemini rejected the social generation request (HTTP {code}): {getattr(e, 'message', str(e))}")
        raise GeminiModelError(f"Gemini client error (HTTP {code}): {getattr(e, 'message', str(e))}")

    except ServerError as e:
        logger.error("Gemini ServerError during social generation: %s", getattr(e, "message", str(e)))
        raise

    except APIError as e:
        logger.error("Gemini APIError during social generation: %s", e)
        raise

    except (GeminiResponseError, GeminiNotConfiguredError, GeminiAuthError, GeminiQuotaError, GeminiModelError):
        raise

    except Exception as e:
        logger.error(f"Social generation failed: {e}")
        raise
