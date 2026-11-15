"""CreateX AI – Social Media API Route"""
from fastapi import APIRouter, HTTPException
from app.schemas.social import SocialRequest, SocialResponse
from app.services.social_service import generate_social

router = APIRouter()


@router.post("/generate", response_model=SocialResponse)
async def generate_social_endpoint(request: SocialRequest):
    """
    Generate platform-specific social media content (Instagram, YouTube).
    Maintains campaign brand identity and tone throughout all outputs.
    """
    try:
        social = await generate_social(request)
        return SocialResponse(success=True, social=social)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Social media generation failed: {str(e)}")
