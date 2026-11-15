"""CreateX AI – Campaign Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional


class BrandColors(BaseModel):
    primary: str = "#7C3AED"
    secondary: str = "#06B6D4"
    accent: str = "#F59E0B"
    background: str = "#0F0F1A"


class CampaignRequest(BaseModel):
    idea: str = Field(..., min_length=10, max_length=2000, description="The creative idea")
    industry: str = Field(..., description="Industry or sector")
    target_audience: str = Field(..., description="Target audience description")
    tone: str = Field(..., description="Campaign tone (e.g. bold, playful, professional)")
    platforms: list[str] = Field(default=["instagram"], description="Target social platforms")
    visual_style: str = Field(default="modern", description="Visual style preference")


class CampaignContext(BaseModel):
    """Shared context passed to all downstream generators for consistency."""
    campaign_name: str
    tagline: str
    description: str
    target_audience: str
    brand_colors: BrandColors
    creative_concepts: list[str]
    visual_direction: str
    writing_tone: str
    poster_generation_prompt: str
    key_messages: list[str]
    campaign_themes: list[str]

    # Original inputs preserved for downstream generators
    original_idea: Optional[str] = None
    industry: Optional[str] = None
    tone: Optional[str] = None
    platforms: Optional[list[str]] = None
    visual_style: Optional[str] = None


class CampaignResponse(BaseModel):
    success: bool = True
    campaign: CampaignContext
