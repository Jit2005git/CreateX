"""CreateX AI – Project & Asset Pydantic Schemas"""
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime
import uuid


class ProjectSave(BaseModel):
    title: str
    original_idea: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
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
    storage_path: Optional[str] = None


class AssetCreateRequest(BaseModel):
    asset_type: str = Field(..., description="Asset type: 'campaign' | 'poster' | 'storyboard' | 'social'")
    content: Optional[dict[str, Any]] = None
    asset_url: Optional[str] = None
    storage_path: Optional[str] = None


class AssetSaveResponse(BaseModel):
    success: bool = True
    asset_id: str
    project_id: str
    asset_type: str
    message: str = "Asset saved successfully"


class AssetResponse(BaseModel):
    id: str
    project_id: str
    asset_type: str
    content: Optional[dict[str, Any]] = None
    asset_url: Optional[str] = None
    storage_path: Optional[str] = None
    created_at: Optional[datetime] = None


class AssetListResponse(BaseModel):
    success: bool = True
    assets: list[AssetResponse]
    total: int


class ProjectResponse(BaseModel):
    id: str
    title: str
    original_idea: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
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
