"""CreateX AI - Storage Service
Unified storage abstraction supporting Supabase Storage and Local Development Storage.
"""
import os
import uuid
import logging
from pathlib import Path
from app.core.config import settings

logger = logging.getLogger(__name__)

# Base local storage directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_STORAGE_DIR = BACKEND_DIR / "storage"
POSTERS_DIR = LOCAL_STORAGE_DIR / "posters"


def ensure_storage_dirs():
    """Ensure local storage directories exist."""
    POSTERS_DIR.mkdir(parents=True, exist_ok=True)


class StorageError(Exception):
    """Raised when an image cannot be saved to storage."""


async def save_poster_image(
    image_bytes: bytes,
    filename: str | None = None,
    mime_type: str = "image/png",
) -> tuple[str, str]:
    """
    Save poster image bytes to Supabase Storage or Local Development Storage.

    Returns:
        tuple[public_url, storage_path]

    Raises:
        StorageError if saving fails.
    """
    if not image_bytes or len(image_bytes) == 0:
        raise StorageError("Cannot store empty image bytes.")

    ext = "png" if "png" in mime_type else "jpg" if "jpeg" in mime_type or "jpg" in mime_type else "png"
    file_name = filename or f"poster_{uuid.uuid4().hex}.{ext}"
    storage_path = f"posters/{file_name}"

    # Check if Supabase is configured
    supabase_configured = bool(
        settings.supabase_url
        and "your-project-id" not in settings.supabase_url
        and settings.supabase_service_role_key
        and "your_supabase" not in settings.supabase_service_role_key
    )

    if supabase_configured:
        try:
            from app.services.supabase_service import upload_image_to_storage
            logger.info("Uploading poster to Supabase Storage: %s", storage_path)
            public_url = await upload_image_to_storage(image_bytes, storage_path, mime_type)
            return public_url, storage_path
        except Exception as e:
            logger.warning(
                "Supabase upload failed (%s). Falling back to local storage.", e
            )

    # Local storage fallback
    try:
        ensure_storage_dirs()
        local_file_path = POSTERS_DIR / file_name
        with open(local_file_path, "wb") as f:
            f.write(image_bytes)

        base_url = (settings.backend_url or "http://localhost:8000").rstrip("/")
        public_url = f"{base_url}/static/posters/{file_name}"
        logger.info("Saved poster to local storage: %s -> %s", local_file_path, public_url)
        return public_url, storage_path

    except Exception as e:
        logger.error("Failed to save image locally: %s", e)
        raise StorageError(f"Failed to save image to storage: {str(e)}")
