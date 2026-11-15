"""CreateX AI – Visual / Poster API Route"""
from fastapi import APIRouter, HTTPException
from app.schemas.visual import VisualRequest, VisualResponse
from app.services.visual_service import generate_poster

router = APIRouter()


@router.post("/generate", response_model=VisualResponse)
async def generate_visual_endpoint(request: VisualRequest):
    """
    Generate a promotional poster image using Gemini image generation.
    Requires a valid CampaignContext. Returns a real Supabase Storage URL.
    Will never return a fabricated or placeholder image URL.
    """
    try:
        result = await generate_poster(request.campaign, request.style_override)
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")
