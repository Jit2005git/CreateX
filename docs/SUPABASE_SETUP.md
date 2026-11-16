# CreateX AI – Supabase Production Architecture & Security Setup Guide

**Document:** `docs/SUPABASE_SETUP.md`  
**Version:** 2.1.0 (Hardened Security Edition)  
**Status:** Architecture Finalized & Verified (Awaiting User Execution Approval)  
**Security Classification:** Strict – Service Role credentials are backend-only.

---

## 1. Architectural Model & Security Foundations

CreateX AI connects to Supabase for two distinct services:
1. **PostgreSQL Database:** Managing user profiles, campaign project metadata, and generated creative assets (storyboards, social copy, posters).
2. **Supabase Storage:** Storing and distributing promotional poster images.

```
┌────────────────────────────────────────────────────────┐
│               Frontend (React / Vite)                 │
│  - Supabase Anon Key (VITE_SUPABASE_ANON_KEY)          │
│  - User Auth Token (JWT) in Authorization Header       │
│  - Local Guest Session Fallback (session_id)           │
└──────────────────────────┬─────────────────────────────┘
                           │ HTTP + Bearer JWT
                           ▼
┌────────────────────────────────────────────────────────┐
│               Backend (FastAPI)                       │
│  - Security Dependency (get_current_identity)          │
│    * Validates Bearer token (rejects invalid with 401) │
│    * Strictly enforces Tenant & Guest Isolation        │
│  - Service Role Key (SUPABASE_SERVICE_ROLE_KEY)       │
│    * Bypasses DB RLS (Backend acts as Policy Enforcer) │
└──────────────────────────┬─────────────────────────────┘
                           │ Service Role Client
                           ▼
┌────────────────────────────────────────────────────────┐
│               Supabase Cloud                           │
│  ├── Auth: auth.users (Email/Password, OAuth)          │
│  ├── Database: projects, generated_assets, profiles    │
│  └── Storage: createx-posters (CDN-backed bucket)      │
└────────────────────────────────────────────────────────┘
```

---

## 2. Security Principles & Enforcement Rules

### 2.1 Strict Bearer Token Validation (No Silent Downgrade)
- If an `Authorization: Bearer <token>` header is present, the backend **strictly validates** the token.
- If the token is invalid, expired, or malformed, the API **immediately rejects the request with HTTP 401 Unauthorized** and `WWW-Authenticate: Bearer`.
- The system **never silently downgrades** an invalid Bearer token to guest mode.
- Only requests that completely omit the `Authorization` header are permitted to use the guest flow (if enabled).

### 2.2 Secure Guest-Session Access & Isolation
- Guest sessions do not imply zero security. An unvalidated nullable `session_id` can lead to cross-guest data leakage or SQL injection.
- **Session ID Format:** All guest session IDs must match `^[a-zA-Z0-9_\-]{8,128}$` (enforced via `validate_session_id`).
- **Tenant Separation:**
  - Authenticated projects store `user_id = <uuid>` and `session_id = NULL`.
  - Guest projects store `user_id = NULL` and `session_id = <guest_id>`.
  - Unauthenticated guests can **never** query or access projects owned by authenticated users (`user_id IS NOT NULL`).
  - Guest A (`session_id = A`) can **never** access or modify Guest B's project (`session_id = B`).

### 2.3 Service-Role Authorization Responsibility
Because the FastAPI backend uses `SUPABASE_SERVICE_ROLE_KEY`, it bypasses database-level Row Level Security. Therefore, **every backend endpoint is an enforcement boundary**:
- `GET /api/projects/{id}`: Verifies project ownership before returning data.
- `POST /api/projects/{id}/assets`: Verifies project ownership before attaching assets.
- `GET /api/projects/{id}/assets`: Verifies project ownership before listing assets.
- `DELETE /api/projects/{id}`: Verifies project ownership before deleting the project and its remote assets.
- If an unauthorized user or guest attempts to access a project, the API responds with **HTTP 404 Not Found** (preventing project existence enumeration).

### 2.4 Profile Tier Protection & Privilege Escalation Prevention
- Standard users must never be able to modify privileged account attributes, specifically `tier` (e.g. escalating from `'free'` to `'pro'`).
- Enforced at both:
  1. **PostgreSQL Trigger Layer:** `protect_profile_tier()` trigger raises an exception if `NEW.tier IS DISTINCT FROM OLD.tier`.
  2. **RLS Policy Layer:** `WITH CHECK (auth.uid() = id)` blocks unauthorized row updates.

### 2.5 Safe `search_path` on `SECURITY DEFINER` Functions
- All `SECURITY DEFINER` functions in PostgreSQL execute with elevated privileges (superuser or owner).
- To prevent search-path hijacking attacks, every function explicitly specifies:
  ```sql
  SET search_path = public, pg_temp;
  ```
- Function execution is revoked from `PUBLIC`, `anon`, and `authenticated`, granted only to internal administrative roles (`supabase_auth_admin` and `service_role`).

---

## 3. Database Schema & Migration Script

This script is **safely rerunnable**. It uses `DROP POLICY IF EXISTS` prior to every `CREATE POLICY`, preventing duplicate policy errors during successive runs.

```sql
-- =============================================================================
-- CreateX AI: Production Supabase Migration
-- Version: 2.1.0
-- =============================================================================

-- 1. Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 2. User Profiles Table
CREATE TABLE IF NOT EXISTS public.profiles (
    id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name   TEXT,
    avatar_url  TEXT,
    tier        TEXT NOT NULL DEFAULT 'free',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Secure Profile Creation Trigger with explicit search_path
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    INSERT INTO public.profiles (id, full_name, avatar_url, tier)
    VALUES (
        NEW.id,
        NEW.raw_user_meta_data->>'full_name',
        NEW.raw_user_meta_data->>'avatar_url',
        'free'
    )
    ON CONFLICT (id) DO NOTHING;
    RETURN NEW;
END;
$$;

-- Restrict function execution permissions
REVOKE ALL ON FUNCTION public.handle_new_user() FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.handle_new_user() FROM anon, authenticated;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'supabase_auth_admin') THEN
        GRANT EXECUTE ON FUNCTION public.handle_new_user() TO supabase_auth_admin;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION public.handle_new_user() TO service_role;
    END IF;
END $$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Tier immutability trigger: prevents users from modifying their own subscription tier
CREATE OR REPLACE FUNCTION public.protect_profile_tier()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    IF NEW.tier IS DISTINCT FROM OLD.tier THEN
        RAISE EXCEPTION 'Privilege modification disallowed: Users cannot alter their own tier.';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_protect_profile_tier ON public.profiles;
CREATE TRIGGER trg_protect_profile_tier
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.protect_profile_tier();

-- 3. Projects Table
CREATE TABLE IF NOT EXISTS public.projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    session_id      TEXT,
    title           TEXT NOT NULL,
    original_idea   TEXT NOT NULL,
    industry        TEXT,
    target_audience TEXT,
    tone            TEXT,
    platforms       JSONB DEFAULT '[]'::jsonb,
    visual_style    TEXT,
    campaign_data   JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Idempotent column additions for upgrades
ALTER TABLE public.projects ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE public.projects ALTER COLUMN session_id DROP NOT NULL;

-- 4. Generated Assets Table
CREATE TABLE IF NOT EXISTS public.generated_assets (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id   UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    asset_type   TEXT NOT NULL,
    content      JSONB,
    asset_url    TEXT,
    storage_path TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.generated_assets ADD COLUMN IF NOT EXISTS storage_path TEXT;

-- 5. Indexes for Query Performance
CREATE INDEX IF NOT EXISTS idx_projects_user_id     ON public.projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_session_id  ON public.projects(session_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at  ON public.projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_project_id    ON public.generated_assets(project_id);
CREATE INDEX IF NOT EXISTS idx_assets_type          ON public.generated_assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_proj_type     ON public.generated_assets(project_id, asset_type);

-- 6. Updated_At Auto-trigger
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS update_projects_updated_at ON public.projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

DROP TRIGGER IF EXISTS update_profiles_updated_at ON public.profiles;
CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

-- =============================================================================
-- Row Level Security (RLS) Policies (Safely Rerunnable)
-- =============================================================================

ALTER TABLE public.profiles         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects         ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.generated_assets ENABLE ROW LEVEL SECURITY;

-- -----------------------------------------------------------------------------
-- Profiles Policies
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can read own profile" ON public.profiles;
CREATE POLICY "Users can read own profile"
    ON public.profiles FOR SELECT
    TO authenticated
    USING (auth.uid() = id);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile"
    ON public.profiles FOR UPDATE
    TO authenticated
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

DROP POLICY IF EXISTS "Deny anon access to profiles" ON public.profiles;
CREATE POLICY "Deny anon access to profiles"
    ON public.profiles FOR ALL
    TO anon
    USING (false);

-- -----------------------------------------------------------------------------
-- Projects Policies
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view their own projects" ON public.projects;
CREATE POLICY "Users can view their own projects"
    ON public.projects FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can insert their own projects" ON public.projects;
CREATE POLICY "Users can insert their own projects"
    ON public.projects FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can update their own projects" ON public.projects;
CREATE POLICY "Users can update their own projects"
    ON public.projects FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users can delete their own projects" ON public.projects;
CREATE POLICY "Users can delete their own projects"
    ON public.projects FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Deny anon direct access to projects" ON public.projects;
CREATE POLICY "Deny anon direct access to projects"
    ON public.projects FOR ALL
    TO anon
    USING (false);

-- -----------------------------------------------------------------------------
-- Generated Assets Policies
-- -----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view assets of their projects" ON public.generated_assets;
CREATE POLICY "Users can view assets of their projects"
    ON public.generated_assets FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE public.projects.id = public.generated_assets.project_id
            AND public.projects.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can insert assets into their projects" ON public.generated_assets;
CREATE POLICY "Users can insert assets into their projects"
    ON public.generated_assets FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE public.projects.id = public.generated_assets.project_id
            AND public.projects.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can delete assets of their projects" ON public.generated_assets;
CREATE POLICY "Users can delete assets of their projects"
    ON public.generated_assets FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE public.projects.id = public.generated_assets.project_id
            AND public.projects.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Users can update assets of their projects" ON public.generated_assets;
CREATE POLICY "Users can update assets of their projects"
    ON public.generated_assets FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE public.projects.id = public.generated_assets.project_id
            AND public.projects.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE public.projects.id = public.generated_assets.project_id
            AND public.projects.user_id = auth.uid()
        )
    );

DROP POLICY IF EXISTS "Deny anon direct access to assets" ON public.generated_assets;
CREATE POLICY "Deny anon direct access to assets"
    ON public.generated_assets FOR ALL
    TO anon
    USING (false);

-- =============================================================================
-- Storage Bucket Configuration
-- =============================================================================

INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'createx-posters',
    'createx-posters',
    true,               -- Public bucket: posters are marketing outputs served via CDN
    10485760,           -- 10 MB per file limit
    ARRAY['image/png', 'image/jpeg', 'image/webp']
)
ON CONFLICT (id) DO UPDATE SET
    public = true,
    file_size_limit = 10485760,
    allowed_mime_types = ARRAY['image/png', 'image/jpeg', 'image/webp'];

-- Storage Access Policies (Safely Rerunnable)
-- Note: Service role automatically bypasses RLS in Supabase Storage; no redundant policies needed.
DROP POLICY IF EXISTS "Public read access for posters" ON storage.objects;
DROP POLICY IF EXISTS "Public read access for createx-posters" ON storage.objects;
CREATE POLICY "Public read access for createx-posters"
    ON storage.objects FOR SELECT
    TO public
    USING (bucket_id = 'createx-posters');
```

---

## 4. Storage Security: Public vs. Private Buckets

### 4.1 Current Bucket: `createx-posters` (Public)
> [!WARNING]
> **PUBLIC EXPOSURE NOTICE:** Files stored in `createx-posters` are accessible to **anyone with the public URL**. No authentication check is performed by the Supabase/Cloudflare CDN when downloading images from this bucket.

- **Intended Use:** Final promotional campaign artwork, marketing assets, and images intended for pitch decks or external distribution.
- **CDN Speed:** Very fast, high cache hit rates, zero API gateway overhead.

### 4.2 Recommendation for Confidential / Sensitive Assets
For enterprise creative work, NDA-governed concept art, internal drafts, or proprietary brand kits, **public buckets are not suitable**.

**Recommended Architecture for Sensitive Assets:**
1. Create a private bucket: `createx-private-assets` (`public = false`).
2. Do not grant public read access (`SELECT TO public USING (false)`).
3. Generate **pre-signed temporary URLs** via the backend:
   ```python
   # Expiration: 3600 seconds (1 hour)
   signed_url = supabase.storage.from_("createx-private-assets").create_signed_url(
       storage_path, 3600
   )
   ```
4. This ensures that only authorized project owners with active sessions can retrieve draft images.

---

## 5. Supabase Key Formats & Environment Configuration

### 5.1 Key Formats in Supabase
Supabase uses two key generations across existing and new projects:
1. **New Projects (2024+):**
   - Publishable Keys: `sb_pub_...`
   - Secret Keys: `sb_sec_...`
2. **Legacy / Standard Projects:**
   - Anon Key: Signed JWT with role `"anon"` (`eyJ...`)
   - Service Role Key: Signed JWT with role `"service_role"` (`eyJ...`)

Both formats are supported by `supabase-py` and `@supabase/supabase-js`.

### 5.2 Environment Variables Breakdown

#### Backend Configuration (`backend/.env` - SECRET)
```env
# Found in: Supabase Dashboard > Project Settings > API
SUPABASE_URL=https://<your-project-id>.supabase.co

# SECRET: Used only by backend services. Grants full admin bypass.
SUPABASE_SERVICE_ROLE_KEY=<your-secret-service-role-key-or-sb_sec_key>

# PUBLIC: Anon key used for client authentication handshakes
SUPABASE_ANON_KEY=<your-anon-jwt-or-sb_pub_key>

# JWT Secret: Found in Project Settings > API > JWT Settings (for fast local JWT decode)
SUPABASE_JWT_SECRET=<your-supabase-jwt-secret>

# Storage Bucket (defaults to createx-posters, 10 MB limit)
SUPABASE_STORAGE_BUCKET=createx-posters

# Application settings
APP_ENV=production
FRONTEND_URL=https://your-domain.com
ALLOWED_ORIGINS=https://your-domain.com
BACKEND_URL=https://api.your-domain.com
```

#### Frontend Configuration (`frontend/.env` - PUBLIC)
```env
VITE_API_BASE_URL=https://api.your-domain.com

# Optional if client initializes Supabase Auth directly:
VITE_SUPABASE_URL=https://<your-project-id>.supabase.co
VITE_SUPABASE_ANON_KEY=<your-anon-jwt-or-sb_pub_key>
```

> [!CAUTION]
> **NEVER** place `SUPABASE_SERVICE_ROLE_KEY` in `frontend/.env` or name it with `VITE_`. Vite embeds all `VITE_*` environment variables directly into client-side JavaScript bundles where anyone can extract them using browser developer tools.

---

## 6. Verification and Security Test Coverage

A dedicated security verification test suite has been implemented in:
`backend/test_supabase_security.py`

### Test Scenarios Covered:
1. **Invalid Token Rejection:**
   - Sending an invalid or expired Bearer token (`Bearer invalid_jwt_token_12345`) returns **HTTP 401 Unauthorized**.
   - The server **does not** silently downgrade to guest mode.
2. **Malformed Authorization Header:**
   - Sending invalid authorization formats (e.g. `Basic abc`, `Token 123`) returns **HTTP 401 Unauthorized**.
3. **Cross-User Project Isolation:**
   - User A creates Project A.
   - User B attempts to read Project A -> returns **HTTP 404 Not Found** (preventing user enumeration).
   - User B attempts to delete Project A -> returns **HTTP 404 Not Found**.
4. **Guest Session Isolation:**
   - Guest A creates Project A with `session_id_A`.
   - Guest B (`session_id_B`) attempts to read Project A -> returns **HTTP 404 Not Found**.
   - Guest B attempts to delete Project A -> returns **HTTP 404 Not Found**.
5. **Guest Cannot Access Authenticated Projects:**
   - Guest attempts to access User A's project -> returns **HTTP 404 Not Found**.
6. **Cross-User Asset Operations:**
   - User B cannot create an asset under User A's project -> returns **HTTP 404 Not Found**.
   - User B cannot list assets belonging to User A's project -> returns **HTTP 404 Not Found**.
7. **Profile Tier Protection:**
   - Database trigger `protect_profile_tier` raises exception on tier alteration.
8. **Guest Session ID Validation:**
   - Sending malicious or malformed `session_id` (e.g. SQL injection strings, empty strings) returns **HTTP 422 Unprocessable Entity**.

---

## 7. Migration Execution Checklist

When you are ready to connect your newly created, empty Supabase project:
- [ ] Create a project in the Supabase Dashboard.
- [ ] Open **SQL Editor**, open or paste `database/schema.sql`, and click **Run**.
- [ ] Verify that `profiles`, `projects`, and `generated_assets` tables exist with RLS enabled.
- [ ] Verify that the `createx-posters` storage bucket exists with:
  - **Public**: `true`
  - **File size limit**: `10 MB` (`10485760` bytes)
  - **Allowed MIME types**: `image/png`, `image/jpeg`, `image/webp`
- [ ] Copy `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `SUPABASE_ANON_KEY` to `backend/.env`.
- [ ] Run `python backend/test_supabase_security.py` to confirm all security boundaries pass.
