-- ─────────────────────────────────────────────────────────────────────────────
-- CreateX AI – Production Database Schema & Security Migrations
-- Version: 2.1.0
--
-- Security Features:
-- 1. Safely rerunnable (DROP POLICY IF EXISTS before CREATE POLICY)
-- 2. Fixed search_path on SECURITY DEFINER functions (prevents search path hijacking)
-- 3. Execution privileges restricted to internal auth administrator
-- 4. Tier immutability trigger preventing privilege escalation on profiles
-- 5. Tenant isolation for authenticated users + guest session boundary enforcement
-- 6. Storage bucket configured; redundant service-role policies removed
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Extensions
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

-- Tier immutability trigger: prevents users from escalating their subscription tier
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

-- 5. Indexes
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
-- Note: Service role automatically bypasses RLS in Supabase Storage; no redundant policies required.
DROP POLICY IF EXISTS "Public read access for posters" ON storage.objects;
DROP POLICY IF EXISTS "Public read access for createx-posters" ON storage.objects;
CREATE POLICY "Public read access for createx-posters"
    ON storage.objects FOR SELECT
    TO public
    USING (bucket_id = 'createx-posters');
