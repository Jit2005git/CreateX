# CreateX AI – System Architecture

## Overview

CreateX AI uses a **modular monolithic** architecture with a clear separation between frontend, backend, and AI orchestration layers.

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                  │
│  Dashboard  │  Create Campaign  │  Creative Workspace           │
│  (3 pages)  │  (4-step form)    │  (4-tab studio)               │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP (Fetch API)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND (FastAPI + Python)                    │
│                                                                 │
│  POST /api/campaign/generate  ──► Campaign Service              │
│  POST /api/visual/generate    ──► Visual Service                │
│  POST /api/storyboard/generate ─► Storyboard Service            │
│  POST /api/social/generate    ──► Social Service                │
│  CRUD /api/projects/*         ──► Supabase Service              │
└──────────────────┬──────────────────────┬───────────────────────┘
                   │                      │
                   ▼                      ▼
        ┌─────────────────┐    ┌──────────────────────┐
        │  Google Gemini  │    │  Supabase            │
        │  - Text (flash) │    │  - PostgreSQL        │
        │  - Image gen    │    │  - Storage (posters) │
        └─────────────────┘    └──────────────────────┘
```

---

## AI Orchestration Pipeline

The key architectural decision is the **shared CampaignContext** — a single object produced by the Campaign Generator and consumed by all downstream generators.

```
User Idea + Inputs
        │
        ▼
  Campaign Generator (Gemini text)
        │
        ▼
  CampaignContext {
    campaign_name, tagline, description,
    target_audience, brand_colors,
    creative_concepts, visual_direction,
    writing_tone, poster_generation_prompt,
    key_messages, campaign_themes
  }
        │
        ├──► Poster Generator    (Gemini image) → Supabase Storage → URL
        ├──► Storyboard Generator (Gemini text) → Scene[] JSON
        └──► Social Generator    (Gemini text)  → Instagram + YouTube content
```

**Why this matters:** All four outputs share the same `brand_colors`, `tagline`, `visual_direction`, and `writing_tone`, ensuring brand consistency without additional orchestration complexity.

---

## Module Responsibilities

| Module | Service | Input | Output |
|--------|---------|-------|--------|
| Campaign Generator | `campaign_service.py` | Idea + form fields | `CampaignContext` |
| Poster Studio | `visual_service.py` | `CampaignContext` | Public image URL (Supabase) |
| Storyboard Studio | `storyboard_service.py` | `CampaignContext` + config | `Scene[]` |
| Social Studio | `social_service.py` | `CampaignContext` | Instagram + YouTube content |
| Project Storage | `supabase_service.py` | Any payload | Persisted record |

---

## Data Flow – Creating a Campaign

1. User fills 4-step form → `POST /api/campaign/generate`
2. Backend calls Gemini with structured prompt → receives JSON
3. JSON validated via Pydantic `CampaignContext`
4. Project auto-saved to Supabase → returns `project_id`
5. Frontend navigates to `/workspace/:projectId`
6. User triggers individual generators from workspace tabs
7. Each generator receives full `CampaignContext` in request body

---

## State Management

**Backend:** Stateless REST API — all context passed in request body.  
**Frontend:** 
- Campaign context stored in `sessionStorage` after generation (immediate access).
- Projects persisted in Supabase for cross-session retrieval.
- No global state manager required at MVP scale.

---

## Security

- `SUPABASE_SERVICE_ROLE_KEY` is **never** sent to the frontend.
- `GEMINI_API_KEY` is **never** exposed in frontend code.
- RLS enabled on all Supabase tables; anon key access denied.
- All env vars loaded via Pydantic `BaseSettings` from `.env`.

---

## Deployment Targets

| Layer | Platform | Config |
|-------|----------|--------|
| Frontend | Vercel | `VITE_API_BASE_URL` env var |
| Backend | Render | All backend env vars |
| Database | Supabase | Managed PostgreSQL |
