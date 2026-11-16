"""CreateX AI - Visual / Poster API Route

Error-to-HTTP mapping (per PROJECT_RULES.md section 4):
  GeminiNotConfiguredError -> 503  (service unavailable - config issue)
  GeminiAuthError          -> 503  (service unavailable - bad key)
  GeminiQuotaError         -> 503  (service unavailable - quota limit)
  GeminiModelError         -> 422  (unprocessable - bad model configuration)
  GeminiResponseError      -> 422  (unprocessable - invalid AI output)
  StorageError             -> 500  (storage persistence failure)
  ServerError              -> 503  (Gemini 5xx)
  Pydantic ValidationError -> 422  (FastAPI handles automatically)
  Any other Exception      -> 500  (unexpected)
"""
from fastapi import APIRouter, HTTPException
from google.genai.errors import ServerError

from app.schemas.visual import VisualRequest, VisualResponse
from app.services.visual_service import (
    generate_poster,
    GeminiNotConfiguredError,
    GeminiAuthError,
    GeminiQuotaError,
    GeminiModelError,
    GeminiResponseError,
    StorageError,
)

router = APIRouter()


@router.post("/generate", response_model=VisualResponse)
async def generate_visual_endpoint(request: VisualRequest):
    """
    Generate a promotional poster image using Gemini image generation.
    Requires a valid CampaignContext. Returns an accessible image URL.
    Will never return a fabricated or placeholder image URL.
    """
    try:
        result = await generate_poster(request.campaign, request.style_override)
        return result

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

    except StorageError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except ServerError as e:
        raise HTTPException(
            status_code=503,
            detail=(
                f"The Gemini image generation service returned an error (HTTP {getattr(e, 'code', 500)}). "
                f"Please try again. Detail: {e.message}"
            ),
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Poster image generation failed: {str(e)}",
        )
