"""CreateX AI – Storyboard Generation Service
Calls Gemini with structured JSON output for scene-by-scene video storyboards.
"""
import json
import logging
import google.genai as genai
from google.genai import types

from app.core.config import settings
from app.core.prompts import STORYBOARD_SYSTEM_PROMPT, STORYBOARD_PROMPT_TEMPLATE
from app.schemas.campaign import CampaignContext
from app.schemas.storyboard import StoryboardData, Scene, StoryboardRequest

logger = logging.getLogger(__name__)


async def generate_storyboard(request: StoryboardRequest) -> StoryboardData:
    """Generate a scene-by-scene video storyboard using the shared campaign context."""
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")

    client = genai.Client(api_key=settings.gemini_api_key)
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
        response = client.models.generate_content(
            model=settings.gemini_text_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=STORYBOARD_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.7,
                max_output_tokens=4096,
            ),
        )

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = raw_text.split("```")[1]
            if raw_text.startswith("json"):
                raw_text = raw_text[4:]
        raw_text = raw_text.strip()

        data = json.loads(raw_text)

        scenes = [Scene(**scene) for scene in data["scenes"]]
        return StoryboardData(
            video_title=data.get("video_title", f"{campaign.campaign_name} – Video"),
            total_duration=data.get("total_duration", request.video_duration),
            platform=data.get("platform", request.platform),
            scenes=scenes,
        )

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse storyboard JSON: {e}")
        raise ValueError(f"AI response was not valid JSON. Please try again. Detail: {e}")
    except Exception as e:
        logger.error(f"Storyboard generation failed: {e}")
        raise
