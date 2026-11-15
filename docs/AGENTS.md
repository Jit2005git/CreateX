# AGENTS.md – CreateX AI Team Guide

This document defines team member responsibilities, file ownership, and collaboration rules.

## Team Composition

### Member 1 – Frontend Engineer
**Responsibility:** React UI, Tailwind styling, routing, component architecture  
**Owns:**
- `frontend/src/pages/`
- `frontend/src/components/`
- `frontend/src/hooks/`
- `frontend/src/utils/`
- `frontend/tailwind.config.js`
- `frontend/index.html`

**Branch:** `feature/frontend`

---

### Member 2 – Backend & Database Engineer
**Responsibility:** FastAPI, Supabase schema, storage, project CRUD  
**Owns:**
- `backend/main.py`
- `backend/app/api/routes/projects.py`
- `backend/app/services/supabase_service.py`
- `backend/app/schemas/project.py`
- `database/schema.sql`
- `backend/.env.example`

**Branch:** `feature/backend-db`

---

### Member 3 – AI & Orchestration Engineer
**Responsibility:** Gemini text generation, prompt engineering, campaign/storyboard/social services  
**Owns:**
- `backend/app/core/prompts.py`
- `backend/app/services/campaign_service.py`
- `backend/app/services/storyboard_service.py`
- `backend/app/services/social_service.py`
- `backend/app/schemas/campaign.py`
- `backend/app/schemas/storyboard.py`
- `backend/app/schemas/social.py`
- `backend/app/api/routes/campaign.py`
- `backend/app/api/routes/storyboard.py`
- `backend/app/api/routes/social.py`

**Branch:** `feature/ai-orchestration`

---

### Member 4 – Image Generation & Integration
**Responsibility:** Gemini image generation, image upload, downloads, end-to-end testing  
**Owns:**
- `backend/app/services/visual_service.py`
- `backend/app/schemas/visual.py`
- `backend/app/api/routes/visual.py`
- Integration test scripts

**Branch:** `feature/image-integration`

---

## Shared Files – Coordination Required

> These files are shared across modules. Coordinate before modifying:

| File | Shared By |
|------|----------|
| `backend/app/schemas/campaign.py` (CampaignContext) | All members |
| `frontend/src/services/api.js` | Members 1 & 4 |
| `docs/API.md` | All members |
| `README.md` | All members |

---

## Git Workflow

```bash
git checkout -b feature/<your-feature>
# work on your module
git push origin feature/<your-feature>
# open PR → review → merge to main
```

**Never commit to `main` directly.**  
**Never commit `.env` files.**

---

## Communication Rules

1. If you need to change a shared file, announce it in the team channel first.
2. Keep route handlers thin — business logic belongs in services.
3. All new API endpoints must be documented in `docs/API.md`.
4. All new Pydantic schemas must use `model_dump()` not `.dict()` (Pydantic v2).
