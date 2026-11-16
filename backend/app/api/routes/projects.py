"""CreateX AI – Projects API Route"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, Depends, Header
from app.schemas.project import (
    ProjectSave,
    AssetSave,
    AssetCreateRequest,
    AssetSaveResponse,
    AssetListResponse,
    SaveResponse,
    ProjectResponse,
    ProjectListResponse,
)
from app.services import supabase_service
from app.core.auth import (
    AuthIdentity,
    get_current_identity,
    validate_session_id,
    verify_project_ownership,
)

router = APIRouter()


@router.post("/save", response_model=SaveResponse)
async def save_project_endpoint(
    payload: ProjectSave,
    identity: AuthIdentity = Depends(get_current_identity),
):
    """Save a campaign project to Supabase, attaching authenticated user_id or validated session_id."""
    try:
        project_dict = payload.model_dump()
        if identity.is_authenticated:
            project_dict["user_id"] = identity.user_id
        else:
            clean_session = validate_session_id(payload.session_id)
            project_dict["session_id"] = clean_session
            project_dict["user_id"] = None

        saved = await supabase_service.save_project(project_dict)
        return SaveResponse(success=True, project_id=saved["id"])
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")


@router.get("", response_model=ProjectListResponse)
async def list_projects_endpoint(
    session_id: Optional[str] = Query(None, description="Demo session ID from client"),
    limit: int = Query(20, ge=1, le=100),
    identity: AuthIdentity = Depends(get_current_identity),
):
    """Return projects for the authenticated user, or for a validated guest session."""
    try:
        if identity.is_authenticated:
            projects = await supabase_service.get_projects(user_id=identity.user_id, limit=limit)
        else:
            clean_session = validate_session_id(session_id)
            projects = await supabase_service.get_projects(session_id=clean_session, limit=limit)

        return ProjectListResponse(success=True, projects=projects, total=len(projects))
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_endpoint(
    project_id: str,
    session_id: Optional[str] = Query(None, description="Guest session ID if unauthenticated"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    identity: AuthIdentity = Depends(get_current_identity),
):
    """Retrieve a single project with its generated assets, strictly verifying ownership."""
    try:
        project = await supabase_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")

        effective_session = x_session_id or session_id
        verify_project_ownership(project, identity, effective_session)

        assets = await supabase_service.get_assets_for_project(project_id)
        project["assets"] = assets
        return project
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project: {str(e)}")


@router.post("/{project_id}/assets", response_model=AssetSaveResponse)
async def save_project_asset_endpoint(
    project_id: str,
    payload: AssetCreateRequest,
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    identity: AuthIdentity = Depends(get_current_identity),
):
    """Save or link a generated creative asset to a project, verifying authorization."""
    try:
        project = await supabase_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")

        effective_session = x_session_id or session_id
        verify_project_ownership(project, identity, effective_session)

        asset_data = {
            "project_id": project_id,
            "asset_type": payload.asset_type,
            "content": payload.content,
            "asset_url": payload.asset_url,
            "storage_path": payload.storage_path,
        }
        saved = await supabase_service.save_asset(asset_data)
        return AssetSaveResponse(
            success=True,
            asset_id=str(saved["id"]),
            project_id=project_id,
            asset_type=payload.asset_type,
            message="Asset saved successfully",
        )
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save asset: {str(e)}")


@router.get("/{project_id}/assets", response_model=AssetListResponse)
async def list_project_assets_endpoint(
    project_id: str,
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    identity: AuthIdentity = Depends(get_current_identity),
):
    """Retrieve all generated creative assets for a project, verifying authorization."""
    try:
        project = await supabase_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")

        effective_session = x_session_id or session_id
        verify_project_ownership(project, identity, effective_session)

        assets = await supabase_service.get_assets_for_project(project_id)
        return AssetListResponse(success=True, assets=assets, total=len(assets))
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project assets: {str(e)}")


@router.delete("/{project_id}")
async def delete_project_endpoint(
    project_id: str,
    session_id: Optional[str] = Query(None),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    identity: AuthIdentity = Depends(get_current_identity),
):
    """Delete a project and all its associated assets, verifying authorization."""
    try:
        project = await supabase_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")

        effective_session = x_session_id or session_id
        verify_project_ownership(project, identity, effective_session)

        # Cleanup remote storage assets if present
        assets = await supabase_service.get_assets_for_project(project_id)
        for a in assets:
            storage_path = a.get("storage_path")
            if storage_path:
                await supabase_service.delete_image_from_storage(storage_path)

        deleted = await supabase_service.delete_project(project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found.")
        return {"success": True, "message": "Project deleted successfully."}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")
