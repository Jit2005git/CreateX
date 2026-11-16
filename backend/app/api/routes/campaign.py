"""
CreateX AI - Campaign API Route

Error-to-HTTP mapping (per PROJECT_RULES.md section 4):
  GeminiNotConfiguredError -> 503  (service unavailable - config issue)
  GeminiAuthError          -> 503  (service unavailable - bad key)
  GeminiQuotaError         -> 503  (service unavailable - quota)
  GeminiModelError         -> 422  (unprocessable - bad model/request config)
  GeminiResponseError      -> 422  (unprocessable - malformed AI output)
  ServerError              -> 503  (Gemini 5xx)
  Pydantic ValidationError -> 422  (FastAPI handles automatically)
  Any other Exception      -> 500  (unexpected)
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from google.genai.errors import ServerError

from app.schemas.campaign import CampaignRequest, CampaignResponse
from app.services.campaign_service import (
    generate_campaign,
    GeminiNotConfiguredError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiModelError,
    GeminiResponseError,
)
from app.core.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)
router = APIRouter()
campaign_limiter = RateLimiter("campaign")


@router.post("/generate", response_model=CampaignResponse)
async def generate_campaign_endpoint(
    request: CampaignRequest,
    _rate_limit: bool = Depends(campaign_limiter),
):
    """
    Generate a full campaign context from a creative idea.

    This is Step 1 of the AI orchestration pipeline.
    Returns a CampaignContext used by all downstream generators
    (poster, storyboard, social media).
    Protected by RateLimiter against quota exhaustion.
    """
    try:
        campaign = await generate_campaign(request)
        return CampaignResponse(success=True, campaign=campaign)

    except GeminiNotConfiguredError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )
    except GeminiAuthError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )
    except GeminiQuotaError as e:
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )
    except GeminiModelError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
    except GeminiResponseError as e:
        raise HTTPException(
            status_code=422,
            detail=str(e),
        )
    except ServerError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"The Gemini API service returned an error (HTTP {getattr(e, 'code', 500)}). "
                f"Please try again. If the problem persists, check https://status.cloud.google.com. "
                f"Detail: {e.message}"
            ),
        )
    except Exception as e:
        logger.exception("Unexpected error during campaign generation: %s", e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during campaign generation. Please try again later.",
        )
