"""CreateX AI – Storyboard Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional
from .campaign import CampaignContext


class StoryboardRequest(BaseModel):
    campaign: CampaignContext
    video_duration: int = Field(default=30, ge=15, le=300, description="Total video duration in seconds")
    num_scenes: int = Field(default=5, ge=3, le=15, description="Number of scenes")
    platform: str = Field(default="instagram", description="Target platform for the video")


class Scene(BaseModel):
    scene_number: int
    duration_seconds: int
    visual_description: str
    camera_direction: str
    narration: str
    on_screen_text: str
    transition: str
    mood: Optional[str] = None


class StoryboardData(BaseModel):
    video_title: str
    total_duration: int
    platform: str
    scenes: list[Scene]


class StoryboardResponse(BaseModel):
    success: bool = True
    storyboard: StoryboardData
