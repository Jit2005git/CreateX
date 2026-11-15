"""CreateX AI – Social Media Pydantic Schemas"""
from pydantic import BaseModel
from typing import Optional
from .campaign import CampaignContext


class SocialRequest(BaseModel):
    campaign: CampaignContext
    platforms: Optional[list[str]] = None  # overrides campaign.platforms if set


class InstagramContent(BaseModel):
    captions: list[str]
    hashtags: list[str]
    cta: str
    story_text: Optional[str] = None


class YouTubeContent(BaseModel):
    title: str
    description: str
    tags: list[str]
    thumbnail_text: Optional[str] = None
    cta: str


class SocialData(BaseModel):
    instagram: Optional[InstagramContent] = None
    youtube: Optional[YouTubeContent] = None
    headlines: list[str]
    ad_copy: Optional[str] = None


class SocialResponse(BaseModel):
    success: bool = True
    social: SocialData
