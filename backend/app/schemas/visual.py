"""CreateX AI – Visual / Poster Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from .campaign import CampaignContext


class VisualRequest(BaseModel):
    campaign: CampaignContext
    style_override: Optional[str] = None  # optional user tweak to the prompt


class VisualResponse(BaseModel):
    success: bool = True
    image_url: str = Field(..., description="Public URL of the generated poster in Supabase Storage")
    storage_path: str = Field(..., description="Internal storage path")
    prompt_used: str = Field(..., description="The exact prompt sent to Gemini")
