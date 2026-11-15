"""CreateX AI – Project & Asset Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
import uuid


class ProjectSave(BaseModel):
    session_id: str
    title: str
    original_idea: str
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    tone: Optional[str] = None
    platforms: Optional[list[str]] = None
    visual_style: Optional[str] = None
    campaign_data: Optional[dict[str, Any]] = None  # full CampaignContext as dict


class AssetSave(BaseModel):
    project_id: str
    asset_type: str  # 'campaign' | 'poster' | 'storyboard' | 'social'
    content: Optional[dict[str, Any]] = None
    asset_url: Optional[str] = None


class AssetResponse(BaseModel):
    id: str
    project_id: str
    asset_type: str
    content: Optional[dict[str, Any]] = None
    asset_url: Optional[str] = None
    created_at: Optional[datetime] = None


class ProjectResponse(BaseModel):
    id: str
    session_id: str
    title: str
    original_idea: str
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    tone: Optional[str] = None
    platforms: Optional[list[str]] = None
    visual_style: Optional[str] = None
    campaign_data: Optional[dict[str, Any]] = None
    assets: Optional[list[AssetResponse]] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class ProjectListResponse(BaseModel):
    success: bool = True
    projects: list[ProjectResponse]
    total: int


class SaveResponse(BaseModel):
    success: bool = True
    project_id: str
    message: str = "Project saved successfully"
