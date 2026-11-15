"""CreateX AI – Projects API Route"""
from fastapi import APIRouter, HTTPException, Query
from app.schemas.project import ProjectSave, AssetSave, SaveResponse, ProjectResponse, ProjectListResponse
from app.services import supabase_service

router = APIRouter()


@router.post("/save", response_model=SaveResponse)
async def save_project_endpoint(payload: ProjectSave):
    """Save a campaign project (and optionally its assets) to Supabase."""
    try:
        saved = await supabase_service.save_project(payload.model_dump())
        return SaveResponse(success=True, project_id=saved["id"])
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")


@router.get("", response_model=ProjectListResponse)
async def list_projects_endpoint(
    session_id: str = Query(..., description="Demo session ID from client"),
    limit: int = Query(20, ge=1, le=100),
):
    """Return all projects for a given session, ordered by newest first."""
    try:
        projects = await supabase_service.get_projects(session_id, limit)
        return ProjectListResponse(success=True, projects=projects, total=len(projects))
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve projects: {str(e)}")


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project_endpoint(project_id: str):
    """Retrieve a single project with its generated assets."""
    try:
        project = await supabase_service.get_project_by_id(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found.")
        assets = await supabase_service.get_assets_for_project(project_id)
        project["assets"] = assets
        return project
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project_endpoint(project_id: str):
    """Delete a project and all its associated assets."""
    try:
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
