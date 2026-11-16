"""CreateX AI – Storyboard API Route"""
import logging
from fastapi import APIRouter, HTTPException
from google.genai.errors import ServerError

from app.schemas.storyboard import StoryboardRequest, StoryboardResponse
from app.services.storyboard_service import (
    generate_storyboard,
    GeminiNotConfiguredError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiModelError,
    GeminiResponseError,
)

logger = logging.getLogger(__name__)
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
    except GeminiNotConfiguredError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiAuthError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiQuotaError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except GeminiModelError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except GeminiResponseError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ServerError as e:
        raise HTTPException(
            status_code=503,
            detail=f"The Gemini API service returned an error. Please try again. Detail: {getattr(e, 'message', str(e))}"
        )
    except ValueError as e:
        if "not configured" in str(e).lower():
            raise HTTPException(status_code=503, detail=str(e))
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during storyboard generation: %s", e)
        raise HTTPException(status_code=500, detail=f"Storyboard generation failed: {str(e)}")
