"""CreateX AI – Social Media Generation Service
Generates platform-optimized captions, hashtags, and copy.
"""
import json
import asyncio
import logging
import google.genai as genai
from google.genai import types
from google.genai.errors import ServerError, APIError

from app.core.config import settings
from app.core.prompts import SOCIAL_SYSTEM_PROMPT, SOCIAL_PROMPT_TEMPLATE
from app.schemas.social import SocialData, SocialRequest, InstagramContent, YouTubeContent

logger = logging.getLogger(__name__)


async def generate_social(request: SocialRequest) -> SocialData:
    """Generate platform-specific social media content maintaining campaign identity."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
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

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        instagram = None
        if "instagram" in data:
            ig = data["instagram"]
            instagram = InstagramContent(
                captions=ig.get("captions", []),
                hashtags=ig.get("hashtags", []),
                cta=ig.get("cta", ""),
                story_text=ig.get("story_text"),
            )

        youtube = None
        if "youtube" in data:
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

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse social JSON: {e}")
        raise ValueError(f"AI response was not valid JSON. Please try again. Detail: {e}")
    except Exception as e:
        logger.error(f"Social generation failed: {e}")
        raise
