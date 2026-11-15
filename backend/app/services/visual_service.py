"""CreateX AI – Visual / Poster Generation Service
Calls Gemini image generation, then uploads to Supabase Storage.
Never returns a fabricated URL — if generation fails, raises an exception.
"""
import io
import uuid
import base64
import logging
import google.genai as genai
from google.genai import types

from app.core.config import settings
from app.schemas.campaign import CampaignContext
from app.schemas.visual import VisualResponse
from app.services.supabase_service import upload_image_to_storage

logger = logging.getLogger(__name__)


def _build_poster_prompt(campaign: CampaignContext, style_override: str | None) -> str:
    base_prompt = campaign.poster_generation_prompt or (
        f"Create a stunning promotional poster for '{campaign.campaign_name}'. "
        f"Tagline: '{campaign.tagline}'. "
        f"Visual direction: {campaign.visual_direction}. "
        f"Use these brand colors: primary {campaign.brand_colors.primary}, "
        f"secondary {campaign.brand_colors.secondary}, accent {campaign.brand_colors.accent}. "
        f"Style: {campaign.visual_style or 'modern, premium, dark'}. "
        f"Include the campaign name and tagline prominently. "
        f"High quality, professional, print-ready design."
    )
    if style_override:
        base_prompt += f" Additional style notes: {style_override}"
    return base_prompt


async def generate_poster(campaign: CampaignContext, style_override: str | None = None) -> VisualResponse:
    """
    Generate a promotional poster image via Gemini and upload it to Supabase Storage.
    Returns the public URL — never a placeholder.
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
    prompt = _build_poster_prompt(campaign, style_override)

    try:
        response = client.models.generate_content(
            model=settings.gemini_image_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            ),
        )

        # Extract image bytes from response
        image_data = None
        mime_type = "image/png"
        
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if hasattr(part, 'inline_data') and part.inline_data:
                    if part.inline_data.mime_type and part.inline_data.mime_type.startswith("image/"):
                        image_data = part.inline_data.data
                        mime_type = part.inline_data.mime_type
                        break

        if image_data is None:
            raise ValueError(
                "Gemini did not return an image. "
                "Check that your API key supports image generation and the model name is correct. "
                f"Model used: {settings.gemini_image_model}"
            )

        # Decode if base64
        if isinstance(image_data, str):
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = bytes(image_data)

        # Upload to Supabase Storage
        file_name = f"poster_{uuid.uuid4().hex}.png"
        storage_path = f"posters/{file_name}"
        public_url = await upload_image_to_storage(image_bytes, storage_path, mime_type)

        return VisualResponse(
            success=True,
            image_url=public_url,
            storage_path=storage_path,
            prompt_used=prompt,
        )

    except Exception as e:
        logger.error(f"Poster generation failed: {e}")
        raise
