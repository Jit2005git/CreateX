"""CreateX AI – Social Media API Route"""
import logging
from fastapi import APIRouter, HTTPException
from google.genai.errors import ServerError

from app.schemas.social import SocialRequest, SocialResponse
from app.services.social_service import (
    generate_social,
    GeminiNotConfiguredError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiModelError,
    GeminiResponseError,
)

logger = logging.getLogger(__name__)
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
        logger.exception("Unexpected error during social content generation: %s", e)
        raise HTTPException(status_code=500, detail=f"Social media generation failed: {str(e)}")
