"""CreateX AI – Supabase Service
All database CRUD and storage operations.
Uses the SERVICE ROLE KEY (never exposed to frontend).
"""
import logging
from typing import Any, Optional
from supabase import create_client, Client

from app.core.config import settings

logger = logging.getLogger(__name__)

_supabase_client: Optional[Client] = None


def is_supabase_configured() -> bool:
    return bool(
        settings.supabase_url
        and "your-project-id" not in settings.supabase_url
        and settings.supabase_service_role_key
        and "your_supabase" not in settings.supabase_service_role_key
    )


def get_supabase() -> Client:
    global _supabase_client
    if _supabase_client is None:
        if not is_supabase_configured():
            raise ValueError(
                "Supabase is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in .env"
            )
        _supabase_client = create_client(settings.supabase_url, settings.supabase_service_role_key)
    return _supabase_client


# ─── IMAGE STORAGE ────────────────────────────────────────────────────────────

async def upload_image_to_storage(image_bytes: bytes, storage_path: str, mime_type: str = "image/png") -> str:
    """Upload image bytes to Supabase Storage and return the public URL."""
    from app.core.config import settings
    supabase = get_supabase()
    bucket = getattr(settings, "supabase_storage_bucket", "createx-posters") or "createx-posters"

    supabase.storage.from_(bucket).upload(
        path=storage_path,
        file=image_bytes,
        file_options={"content-type": mime_type, "upsert": "true"},
    )

    public_url = supabase.storage.from_(bucket).get_public_url(storage_path)
    return public_url


async def delete_image_from_storage(storage_path: str) -> None:
    """Delete an image from Supabase Storage."""
    from app.core.config import settings
    supabase = get_supabase()
    bucket = getattr(settings, "supabase_storage_bucket", "createx-posters") or "createx-posters"
    try:
        supabase.storage.from_(bucket).remove([storage_path])
    except Exception as e:
        logger.warning("Failed to delete storage object %s: %s", storage_path, e)


# ─── PROJECTS ─────────────────────────────────────────────────────────────────

async def save_project(project_data: dict[str, Any]) -> dict[str, Any]:
    supabase = get_supabase()
    result = supabase.table("projects").insert(project_data).execute()
    if not result.data:
        raise ValueError("Failed to save project to database.")
    return result.data[0]


async def get_projects(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    supabase = get_supabase()
    query = supabase.table("projects").select("*").order("created_at", desc=True).limit(limit)
    if user_id:
        query = query.eq("user_id", user_id)
    elif session_id:
        query = query.eq("session_id", session_id).is_("user_id", "null")
    else:
        return []
    result = query.execute()
    return result.data or []


async def get_project_by_id(project_id: str) -> Optional[dict[str, Any]]:
    supabase = get_supabase()
    result = supabase.table("projects").select("*").eq("id", project_id).limit(1).execute()
    return result.data[0] if (result and result.data) else None


async def delete_project(project_id: str) -> bool:
    supabase = get_supabase()
    result = supabase.table("projects").delete().eq("id", project_id).execute()
    return bool(result.data)


# ─── ASSETS ──────────────────────────────────────────────────────────────────

async def save_asset(asset_data: dict[str, Any]) -> dict[str, Any]:
    supabase = get_supabase()
    result = supabase.table("generated_assets").insert(asset_data).execute()
    if not result.data:
        raise ValueError("Failed to save asset to database.")
    return result.data[0]


async def get_assets_for_project(project_id: str) -> list[dict[str, Any]]:
    supabase = get_supabase()
    result = (
        supabase.table("generated_assets")
        .select("*")
        .eq("project_id", project_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []


async def get_asset_by_id(asset_id: str) -> Optional[dict[str, Any]]:
    supabase = get_supabase()
    result = supabase.table("generated_assets").select("*").eq("id", asset_id).limit(1).execute()
    return result.data[0] if (result and result.data) else None


async def delete_asset(asset_id: str) -> bool:
    supabase = get_supabase()
    result = supabase.table("generated_assets").delete().eq("id", asset_id).execute()
    return bool(result.data)


async def delete_assets_for_project(project_id: str) -> None:
    supabase = get_supabase()
    supabase.table("generated_assets").delete().eq("project_id", project_id).execute()
