"""
CreateX AI - FastAPI Application Entry Point
"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.api.routes import campaign, visual, storyboard, social, projects
from app.services.storage_service import LOCAL_STORAGE_DIR, ensure_storage_dirs

# Ensure storage directories exist
ensure_storage_dirs()

app = FastAPI(
    title="CreateX AI API",
    description="AI-powered creative production platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- STATIC STORAGE ---
app.mount("/static", StaticFiles(directory=str(LOCAL_STORAGE_DIR)), name="static")

# --- ROUTES ---
app.include_router(campaign.router,    prefix="/api/campaign",   tags=["Campaign"])
app.include_router(visual.router,      prefix="/api/visual",     tags=["Visual"])
app.include_router(storyboard.router,  prefix="/api/storyboard", tags=["Storyboard"])
app.include_router(social.router,      prefix="/api/social",     tags=["Social"])
app.include_router(projects.router,    prefix="/api/projects",   tags=["Projects"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "CreateX AI API is running", "version": "1.0.0"}


@app.get("/api/health", tags=["Health"])
async def health():
    from app.services.supabase_service import is_supabase_configured
    return {
        "status": "ok",
        "environment": settings.app_env,
        "gemini_configured": bool(settings.gemini_api_key),
        "supabase_configured": is_supabase_configured(),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
