-- ─────────────────────────────────────────────────────────────────────────────
-- CreateX AI – Rollback Migration: 20261117_001_rate_limit_events_rollback.sql
-- Description: Reverts the rate_limit_events table and associated stored procedures
-- ─────────────────────────────────────────────────────────────────────────────

DROP FUNCTION IF EXISTS public.cleanup_rate_limit_events(INT, INT);
DROP FUNCTION IF EXISTS public.check_rate_limit(TEXT, INT, INT);
DROP TABLE IF EXISTS public.rate_limit_events;
