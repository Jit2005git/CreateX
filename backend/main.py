"""
CreateX AI - FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import campaign, visual, storyboard, social, projects

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
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    return {
        "status": "ok",
        "environment": settings.app_env,
        "gemini_configured": bool(settings.gemini_api_key),
        "supabase_configured": bool(settings.supabase_url and settings.supabase_service_role_key),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
