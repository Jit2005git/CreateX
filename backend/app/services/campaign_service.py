"""
CreateX AI - Campaign Generation Service

Calls Gemini text model (via async client) to produce a structured CampaignContext.

Key design decisions:
- Uses client.aio.models.generate_content (async path) because the sync path
  client.models.generate_content blocks the event loop in an async FastAPI handler.
- Distinguishes API-key errors (401 -> 503), quota errors (429 -> 503),
  model errors (400 -> 422).
- JSON from Gemini is stripped of markdown fences then validated via Pydantic.
- API keys are never logged; only key status (configured/missing) is noted.
"""
import json
import logging
import google.genai as genai
from google.genai import types
from google.genai.errors import ClientError, ServerError, APIError

from app.core.config import settings
from app.core.prompts import CAMPAIGN_SYSTEM_PROMPT, CAMPAIGN_PROMPT_TEMPLATE
from app.schemas.campaign import CampaignContext, CampaignRequest, BrandColors

logger = logging.getLogger(__name__)


# --- Custom exception types for route-level error mapping ---

class GeminiNotConfiguredError(Exception):
    """Raised when GEMINI_API_KEY is missing or empty."""


class GeminiAuthError(Exception):
    """Raised when the API key is invalid (HTTP 401/403)."""


class GeminiQuotaError(Exception):
    """Raised when the quota is exceeded (HTTP 429)."""


class GeminiModelError(Exception):
    """Raised when the model name is invalid or the request is malformed (HTTP 400)."""


class GeminiResponseError(Exception):
    """Raised when Gemini returns a response that cannot be parsed into CampaignContext."""


# --- Client factory ---

def _get_gemini_client() -> genai.Client:
    """Return a configured Gemini client. Raises GeminiNotConfiguredError if key is absent."""
    if not settings.gemini_api_key:
        raise GeminiNotConfiguredError(
            "GEMINI_API_KEY is not configured. "
            "Copy backend/.env.example to backend/.env and add your Gemini API key."
        )
    return genai.Client(api_key=settings.gemini_api_key)


# --- JSON extraction helper ---

def _extract_json(raw_text: str) -> dict:
    """
    Strip markdown code fences and parse JSON.
    Gemini sometimes wraps responses in ```json ... ``` even with response_mime_type set.
    """
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop first line (``` or ```json) and last ``` line
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise GeminiResponseError(
            f"Gemini returned a response that is not valid JSON. "
            f"Detail: {e}. "
            f"Raw response (first 300 chars): {raw_text[:300]!r}"
        )


# --- CampaignContext builder ---

def _build_context(data: dict, request: CampaignRequest) -> CampaignContext:
    """
    Convert the parsed Gemini JSON dict into a validated CampaignContext.
    Required fields: campaign_name, tagline, description.
    All other fields fall back to sensible defaults if Gemini omits them.
    """
    missing = [f for f in ("campaign_name", "tagline", "description") if not data.get(f)]
    if missing:
        raise GeminiResponseError(
            f"Gemini response is missing required fields: {missing}. "
            "This may indicate an issue with the prompt or the model. Please retry."
        )

    brand_colors_raw = data.get("brand_colors") or {}
    brand_colors = BrandColors(
        primary=brand_colors_raw.get("primary") or "#7C3AED",
        secondary=brand_colors_raw.get("secondary") or "#06B6D4",
        accent=brand_colors_raw.get("accent") or "#F59E0B",
        background=brand_colors_raw.get("background") or "#0F0F1A",
    )

    return CampaignContext(
        campaign_name=data["campaign_name"],
        tagline=data["tagline"],
        description=data["description"],
        target_audience=data.get("target_audience") or request.target_audience,
        brand_colors=brand_colors,
        creative_concepts=data.get("creative_concepts") or [],
        visual_direction=data.get("visual_direction") or "",
        writing_tone=data.get("writing_tone") or request.tone,
        poster_generation_prompt=data.get("poster_generation_prompt") or "",
        key_messages=data.get("key_messages") or [],
        campaign_themes=data.get("campaign_themes") or [],
        # Preserve original inputs for downstream generators
        original_idea=request.idea,
        industry=request.industry,
        tone=request.tone,
        platforms=request.platforms,
        visual_style=request.visual_style,
    )


# --- Main service function ---

async def generate_campaign(request: CampaignRequest) -> CampaignContext:
    client = _get_gemini_client()

    prompt = CAMPAIGN_PROMPT_TEMPLATE.format(
        idea=request.idea,
        industry=request.industry,
        target_audience=request.target_audience,
        tone=request.tone,
        platforms=", ".join(request.platforms),
        visual_style=request.visual_style,
    )

    logger.info(
        "Generating campaign: idea_len=%d, industry=%r, tone=%r, model=%r",
        len(request.idea),
        request.industry,
        request.tone,
        settings.gemini_text_model,
    )

    try:
        # Use the async interface - client.aio.models.generate_content is a coroutine
        response = await client.aio.models.generate_content(
            model=settings.gemini_text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=CAMPAIGN_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.8,
                max_output_tokens=2048,
            ),
        )

    except ClientError as e:
        # HTTP 4xx from Gemini API
        code = getattr(e, "code", 0) or 0
        logger.warning("Gemini ClientError %s: %s", code, e.message)
        if code in (401, 403):
            raise GeminiAuthError(
                f"Gemini API key is invalid or does not have permission to use "
                f"model '{settings.gemini_text_model}'. "
                f"Check your GEMINI_API_KEY in backend/.env. (HTTP {code})"
            )
        if code == 429:
            raise GeminiQuotaError(
                "Gemini API quota or rate limit exceeded. "
                "Wait a moment and try again, or check your usage at ai.google.dev. (HTTP 429)"
            )
        if code == 400:
            raise GeminiModelError(
                f"Gemini rejected the request (HTTP 400). "
                f"This often means the model name is invalid. "
                f"Current GEMINI_TEXT_MODEL='{settings.gemini_text_model}'. "
                f"Detail: {e.message}"
            )
        # Other 4xx
        raise GeminiModelError(f"Gemini API client error (HTTP {code}): {e.message}")

    except ServerError as e:
        code = getattr(e, "code", 500) or 500
        logger.error("Gemini ServerError %s: %s", code, e.message)
        raise  # Re-raise for route handler to map to 503

    except APIError as e:
        logger.error("Gemini APIError: %s", e)
        raise

    # Validate response text
    if not response.text:
        raise GeminiResponseError(
            "Gemini returned an empty response. "
            "This may be due to safety filters or an unsupported request. "
            "Try rephrasing your creative idea."
        )

    logger.info("Gemini responded with %d chars", len(response.text))

    data = _extract_json(response.text)
    context = _build_context(data, request)

    logger.info(
        "Campaign generated: name=%r, tagline=%r",
        context.campaign_name,
        context.tagline,
    )
    return context
