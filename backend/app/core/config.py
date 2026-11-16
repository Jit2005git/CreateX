"""
CreateX AI - Application Configuration
Loads all settings from environment variables via Pydantic BaseSettings.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Path to backend/.env regardless of current working directory
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    # Gemini
    gemini_api_key: str = ""
    gemini_text_model: str = "gemini-3.1-flash-lite"
    gemini_image_model: str = "gemini-2.5-flash-image"

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""
    supabase_jwt_secret: str = ""
    supabase_storage_bucket: str = "createx-posters"

    # App
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"
    allowed_origins: str = ""
    app_env: str = "development"

    # Security & Testing
    allow_test_tokens: bool = False

    # Network & Reverse Proxy Trust
    # Comma-separated list of trusted proxy IPs or CIDR networks (IPv4/IPv6).
    # If empty, all forwarded headers (e.g. X-Forwarded-For) are ignored and socket IP is used.
    # Example: "127.0.0.1,::1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    trusted_proxies: str = ""

    # Rate Limiting & Storage Backend
    # Default to "memory" for immediate MVP launch without unverified DB migrations.
    # Supports "postgres" (requires migration 20261117_001 on Supabase) or "redis".
    rate_limit_store_type: str = "memory"
    redis_url: str = ""
    rate_limit_enabled: bool = True
    rate_limit_campaign_per_minute: int = 5
    rate_limit_campaign_auth_per_minute: int = 15
    rate_limit_campaign_ip_per_minute: int = 25
    rate_limit_visual_per_minute: int = 3
    rate_limit_visual_auth_per_minute: int = 10
    rate_limit_visual_ip_per_minute: int = 20

    @property
    def is_production(self) -> bool:
        return self.app_env.strip().lower() in ("production", "prod")

    def validate_production_safety(self) -> None:
        """Validate production safety invariants and fail startup if compromised."""
        if self.is_production:
            if self.allow_test_tokens:
                raise ValueError("FATAL: allow_test_tokens must NEVER be enabled when APP_ENV=production.")

    @property
    def cors_origins(self) -> list[str]:
        """
        Returns validated, explicit CORS allowed origins.
        Strictly disallows wildcard '*' when credentials are true (W3C CORS spec).
        """
        origins: list[str] = []

        def _add_origin(url: str):
            clean = url.strip().rstrip("/")
            if clean and clean != "*" and clean not in origins:
                origins.append(clean)

        # Primary configured frontend URL
        if self.frontend_url:
            _add_origin(self.frontend_url)

        # Additional explicitly configured origins from ALLOWED_ORIGINS env var
        if self.allowed_origins:
            for item in self.allowed_origins.split(","):
                _add_origin(item)

        # Default local origins in development mode only
        if self.app_env == "development":
            for dev_origin in [
                "http://localhost:5173",
                "http://localhost:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:3000",
            ]:
                _add_origin(dev_origin)

        return origins or ["http://localhost:5173"]

    model_config = {
        "env_file": (ENV_PATH, ".env"),
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
