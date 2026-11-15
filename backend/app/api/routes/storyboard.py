"""CreateX AI – Storyboard API Route"""
from fastapi import APIRouter, HTTPException
from app.schemas.storyboard import StoryboardRequest, StoryboardResponse
from app.services.storyboard_service import generate_storyboard

router = APIRouter()


@router.post("/generate", response_model=StoryboardResponse)
async def generate_storyboard_endpoint(request: StoryboardRequest):
    """
    Generate a scene-by-scene video storyboard from campaign context.
    Returns structured JSON with per-scene visual, camera, and narration data.
    """
    try:
        storyboard = await generate_storyboard(request)
        return StoryboardResponse(success=True, storyboard=storyboard)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storyboard generation failed: {str(e)}")
