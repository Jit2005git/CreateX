"""
CreateX AI – Application Configuration
Loads all settings from environment variables via Pydantic BaseSettings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""
    gemini_text_model: str = "gemini-2.0-flash"
    gemini_image_model: str = "gemini-2.0-flash-preview-image-generation"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""

    # App
    frontend_url: str = "http://localhost:5173"
    app_env: str = "development"

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
