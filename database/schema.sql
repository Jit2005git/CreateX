-- ─────────────────────────────────────────────────────────────────────────────
-- CreateX AI – Database Schema
-- Run this in your Supabase SQL Editor to initialize the database.
-- ─────────────────────────────────────────────────────────────────────────────

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── TABLE: projects ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS projects (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      TEXT NOT NULL,                  -- demo session, no auth needed
    title           TEXT NOT NULL,
    original_idea   TEXT NOT NULL,
    industry        TEXT,
    target_audience TEXT,
    tone            TEXT,
    platforms       JSONB DEFAULT '[]'::jsonb,
    visual_style    TEXT,
    campaign_data   JSONB,                          -- full CampaignContext JSON
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ─── TABLE: generated_assets ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS generated_assets (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id  UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    asset_type  TEXT NOT NULL,                      -- 'campaign'|'poster'|'storyboard'|'social'
    content     JSONB,                              -- structured asset data
    asset_url   TEXT,                              -- Supabase Storage URL for images
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ─── INDEXES ─────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_projects_session_id ON projects(session_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_assets_project_id   ON generated_assets(project_id);
CREATE INDEX IF NOT EXISTS idx_assets_type         ON generated_assets(asset_type);

-- ─── UPDATED_AT TRIGGER ──────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ─── ROW LEVEL SECURITY ───────────────────────────────────────────────────────
-- RLS is enabled but service role key (backend only) bypasses all policies.
-- The anon key is NOT exposed to the frontend — all DB access is via backend.

ALTER TABLE projects         ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_assets ENABLE ROW LEVEL SECURITY;

-- Policy: service role has full access (bypasses RLS automatically in Supabase)
-- Policy: anon users cannot access anything directly
CREATE POLICY "Deny anon access to projects"
    ON projects FOR ALL
    TO anon
    USING (false);

CREATE POLICY "Deny anon access to assets"
    ON generated_assets FOR ALL
    TO anon
    USING (false);

-- ─── SUPABASE STORAGE BUCKET ─────────────────────────────────────────────────
-- Run this separately in Supabase Dashboard > Storage, or via the management API.
-- Bucket name: createx-posters
-- Public bucket: true (so generated image URLs are publicly accessible)
--
-- Equivalent SQL (Supabase storage schema):
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'createx-posters',
    'createx-posters',
    true,
    10485760,           -- 10 MB limit per file
    ARRAY['image/png', 'image/jpeg', 'image/webp']
)
ON CONFLICT (id) DO NOTHING;

-- Storage policy: service role can upload
CREATE POLICY "Service role can upload posters"
    ON storage.objects FOR INSERT
    TO service_role
    WITH CHECK (bucket_id = 'createx-posters');

CREATE POLICY "Service role can delete posters"
    ON storage.objects FOR DELETE
    TO service_role
    USING (bucket_id = 'createx-posters');

-- Storage policy: anyone can read public posters
CREATE POLICY "Public read access for posters"
    ON storage.objects FOR SELECT
    TO public
    USING (bucket_id = 'createx-posters');
