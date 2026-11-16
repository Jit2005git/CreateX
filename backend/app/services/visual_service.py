"""CreateX AI - Visual / Poster Generation Service
Calls Gemini image generation and persists the resulting image via storage_service.
Never returns a fabricated URL - if generation fails, raises an appropriate exception.
"""
import uuid
import base64
import logging
import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError, ServerError, APIError

from app.core.config import settings
from app.core.prompts import POSTER_PROMPT_TEMPLATE
from app.schemas.campaign import CampaignContext
from app.schemas.visual import VisualResponse
from app.services.storage_service import save_poster_image, StorageError

logger = logging.getLogger(__name__)


# --- Custom Exception Classes ---

class GeminiNotConfiguredError(Exception):
    """Raised when GEMINI_API_KEY is missing or empty."""


class GeminiAuthError(Exception):
    """Raised when the API key is invalid (HTTP 401/403)."""


class GeminiQuotaError(Exception):
    """Raised when the image generation quota is exceeded (HTTP 429)."""


class GeminiModelError(Exception):
    """Raised when the image model name is invalid or unsupported (HTTP 400/404)."""


class GeminiResponseError(Exception):
    """Raised when Gemini returns an empty or invalid image response."""


def _get_gemini_client() -> genai.Client:
    """Return a configured Gemini client. Raises GeminiNotConfiguredError if key is absent."""
    if not settings.gemini_api_key or settings.gemini_api_key == "your_gemini_api_key_here":
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not configured. "
            "Copy backend/.env.example to backend/.env and add your Gemini API key."
        )
    return genai.Client(api_key=settings.gemini_api_key)


def _build_poster_prompt(campaign: CampaignContext, style_override: str | None = None) -> str:
    """
    Construct a rich, detailed prompt for promotional poster generation.
    Incorporates:
      - Campaign name
      - Original campaign idea / description
      - Brand colors (primary, secondary, accent, background)
      - Visual direction
      - Target audience
      - Campaign tone
      - Selected poster style
      - Optional user style override
    """
    style_override_text = f"Additional Creative Notes: {style_override.strip()}" if style_override else ""

    return POSTER_PROMPT_TEMPLATE.format(
        campaign_name=campaign.campaign_name,
        original_idea=campaign.original_idea or campaign.description,
        tagline=campaign.tagline,
        visual_direction=campaign.visual_direction or "Modern, dynamic creative direction with bold visual elements.",
        primary_color=campaign.brand_colors.primary,
        secondary_color=campaign.brand_colors.secondary,
        accent_color=campaign.brand_colors.accent,
        bg_color=campaign.brand_colors.background,
        target_audience=campaign.target_audience or "General audience",
        tone=campaign.tone or campaign.writing_tone or "Bold and inspiring",
        visual_style=campaign.visual_style or "Modern commercial graphic design",
        style_override=style_override_text,
    ).strip()


def extract_image_bytes(response) -> tuple[bytes, str]:
    """
    Extract raw image bytes and mime type from Gemini GenerateContentResponse candidates.
    Raises GeminiResponseError if no image data is found or data is invalid.
    """
    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        if not content:
            continue
        parts = getattr(content, "parts", None) or []
        for part in parts:
            inline = getattr(part, "inline_data", None)
            if inline and inline.data:
                mime_type = getattr(inline, "mime_type", "image/png") or "image/png"
                raw_data = inline.data
                try:
                    if isinstance(raw_data, str):
                        image_bytes = base64.b64decode(raw_data)
                    else:
                        image_bytes = bytes(raw_data)
                except Exception as e:
                    raise GeminiResponseError(f"Failed to decode image data from Gemini: {e}")

                if len(image_bytes) < 100:
                    raise GeminiResponseError("Gemini returned truncated or empty image bytes.")

                return image_bytes, mime_type

    raise GeminiResponseError(
        f"Gemini did not return an image part in the response. "
        f"Model used: '{settings.gemini_image_model}'. "
        f"Verify that this model supports image output and your API key has quota."
    )


async def generate_poster(
    campaign: CampaignContext,
    style_override: str | None = None,
) -> VisualResponse:
    """
    Generate a promotional poster image via Gemini and persist it to storage.
    Returns VisualResponse with a valid, accessible image_url.
    Never returns a placeholder or fake URL.
    """
    client = _get_gemini_client()
    prompt = _build_poster_prompt(campaign, style_override)

    logger.info(
        "Generating poster for campaign '%s' using model '%s'",
        campaign.campaign_name,
        settings.gemini_image_model,
    )

    try:
        response = await client.aio.models.generate_content(
            model=settings.gemini_image_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )
    except ClientError as e:
        code = getattr(e, "code", 0) or 0
        logger.warning("Gemini ClientError %s during image generation: %s", code, e.message)
        if code in (401, 403):
            raise GeminiAuthError(
                f"Gemini API key is invalid or does not have permission to use image model "
                f"'{settings.gemini_image_model}'. Check your GEMINI_API_KEY in backend/.env. (HTTP {code})"
            )
        if code == 429:
            raise GeminiQuotaError(
                f"Gemini image generation quota exceeded for model '{settings.gemini_image_model}'. "
                f"Please verify your API tier/billing at ai.google.dev. (HTTP 429)"
            )
        if code in (400, 404):
            raise GeminiModelError(
                f"Gemini image model error (HTTP {code}): The model '{settings.gemini_image_model}' "
                f"is not supported or unavailable. Detail: {e.message}"
            )
        raise GeminiModelError(f"Gemini image generation client error (HTTP {code}): {e.message}")

    except ServerError as e:
        code = getattr(e, "code", 500) or 500
        logger.error("Gemini ServerError %s during image generation: %s", code, e.message)
        raise

    except APIError as e:
        logger.error("Gemini APIError during image generation: %s", e)
        raise

    # Extract image bytes
    image_bytes, mime_type = extract_image_bytes(response)

    # Persist image to storage
    file_name = f"poster_{uuid.uuid4().hex[:12]}.png"
    try:
        public_url, storage_path = await save_poster_image(
            image_bytes=image_bytes,
            filename=file_name,
            mime_type=mime_type,
        )
    except StorageError:
        raise
    except Exception as e:
        raise StorageError(f"Unexpected error saving poster to storage: {e}")

    logger.info("Successfully generated and saved poster: %s", public_url)

    return VisualResponse(
        success=True,
        image_url=public_url,
        storage_path=storage_path,
        prompt_used=prompt,
    )
