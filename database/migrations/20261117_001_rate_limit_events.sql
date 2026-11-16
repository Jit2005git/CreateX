-- ─────────────────────────────────────────────────────────────────────────────
-- CreateX AI – Migration: 20261117_001_rate_limit_events.sql
-- Description: PostgreSQL Sliding-Log Atomic Rate Limiter
--
-- Performance & Concurrency Features:
-- 1. UNLOGGED TABLE: High throughput with zero Write-Ahead Log (WAL) I/O overhead.
--    NOTE ON RESTARTS: Unlogged tables are automatically truncated (wiped) upon
--    PostgreSQL crash or unexpected restart. This is safe, intended, and standard
--    for transient 60-second rate-limit counters (identical to Redis restarting).
-- 2. TRANSACTION ADVISORY LOCKS: pg_advisory_xact_lock serializes concurrent requests
--    sharing the same bucket key, guaranteeing strict atomicity across all instances.
-- 3. REJECTED REQUEST PROTECTION: Only allowed requests insert timestamps.
-- 4. SECURITY DEFINER with fixed search_path (public, pg_temp) preventing hijacking.
-- 5. ROLE HARDENING: Execution and table access restricted strictly to service_role;
--    explicitly revoked from anon, authenticated, and public.
-- ─────────────────────────────────────────────────────────────────────────────

-- 1. Table: rate_limit_events
CREATE UNLOGGED TABLE IF NOT EXISTS public.rate_limit_events (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bucket_key   TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for sliding-window lookup and prune operations
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_lookup
    ON public.rate_limit_events (bucket_key, requested_at DESC);

CREATE INDEX IF NOT EXISTS idx_rate_limit_events_cleanup
    ON public.rate_limit_events (requested_at);

-- 2. Access Control on Table
ALTER TABLE public.rate_limit_events ENABLE ROW LEVEL SECURITY;

REVOKE ALL ON TABLE public.rate_limit_events FROM PUBLIC;
REVOKE ALL ON TABLE public.rate_limit_events FROM anon, authenticated;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT SELECT, INSERT, DELETE ON TABLE public.rate_limit_events TO service_role;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        GRANT ALL ON TABLE public.rate_limit_events TO postgres;
    END IF;
END $$;


-- 3. Atomic Sliding-Window Rate Limit Function
CREATE OR REPLACE FUNCTION public.check_rate_limit(
    p_key          TEXT,
    p_max_requests INT,
    p_window_secs  INT
)
RETURNS TABLE (
    allowed        BOOLEAN,
    remaining      INT,
    retry_after    INT
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_now          TIMESTAMPTZ := CLOCK_TIMESTAMP();
    v_window_start TIMESTAMPTZ;
    v_count        INT;
    v_earliest     TIMESTAMPTZ;
    v_retry_after  INT := 0;
    v_lock_id      BIGINT;
BEGIN
    -- 1. Parameter Validation
    IF p_key IS NULL OR LENGTH(TRIM(p_key)) = 0 OR LENGTH(p_key) > 256 THEN
        RAISE EXCEPTION 'check_rate_limit: invalid p_key parameter (must be 1-256 characters)';
    END IF;

    IF p_max_requests IS NULL OR p_max_requests <= 0 OR p_max_requests > 10000 THEN
        RAISE EXCEPTION 'check_rate_limit: invalid p_max_requests parameter (must be 1-10000)';
    END IF;

    IF p_window_secs IS NULL OR p_window_secs <= 0 OR p_window_secs > 86400 THEN
        RAISE EXCEPTION 'check_rate_limit: invalid p_window_secs parameter (must be 1-86400)';
    END IF;

    v_window_start := v_now - (p_window_secs || ' seconds')::INTERVAL;

    -- 2. Deterministic 64-bit integer advisory lock key derived from bucket string
    v_lock_id := ('x' || SUBSTR(MD5(p_key), 1, 16))::BIT(64)::BIGINT;

    -- 3. Acquire transaction-scoped exclusive advisory lock
    -- Automatically released when current transaction ends
    PERFORM pg_advisory_xact_lock(v_lock_id);

    -- 4. Prune expired timestamps for this key within the transaction
    DELETE FROM public.rate_limit_events
    WHERE bucket_key = p_key AND requested_at <= v_window_start;

    -- 5. Count active requests within the active sliding window
    SELECT COUNT(*), MIN(requested_at)
    INTO v_count, v_earliest
    FROM public.rate_limit_events
    WHERE bucket_key = p_key;

    -- 6. Check limit threshold
    IF v_count >= p_max_requests THEN
        -- Exceeded: calculate exact seconds until earliest request rolls out of sliding window
        v_retry_after := GREATEST(1, EXTRACT(EPOCH FROM (v_earliest + (p_window_secs || ' seconds')::INTERVAL - v_now))::INT);
        -- CRITICAL: Do NOT insert timestamp for rejected requests
        RETURN QUERY SELECT false, 0, v_retry_after;
        RETURN;
    END IF;

    -- 7. Permitted: insert new request timestamp
    INSERT INTO public.rate_limit_events (bucket_key, requested_at)
    VALUES (p_key, v_now);

    RETURN QUERY SELECT true, p_max_requests - (v_count + 1), 0;
    RETURN;
END;
$$;

-- Restrict function execution permissions
REVOKE ALL ON FUNCTION public.check_rate_limit(TEXT, INT, INT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.check_rate_limit(TEXT, INT, INT) FROM anon, authenticated;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION public.check_rate_limit(TEXT, INT, INT) TO service_role;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        GRANT EXECUTE ON FUNCTION public.check_rate_limit(TEXT, INT, INT) TO postgres;
    END IF;
END $$;


-- 4. Bounded Cleanup Function (removes events older than retention period in safe batches)
CREATE OR REPLACE FUNCTION public.cleanup_rate_limit_events(
    p_retention_secs INT DEFAULT 300,
    p_batch_size     INT DEFAULT 5000
)
RETURNS INT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_cutoff  TIMESTAMPTZ := CLOCK_TIMESTAMP() - (p_retention_secs || ' seconds')::INTERVAL;
    v_deleted INT := 0;
BEGIN
    IF p_retention_secs IS NULL OR p_retention_secs < 60 THEN
        p_retention_secs := 300;
    END IF;

    IF p_batch_size IS NULL OR p_batch_size <= 0 OR p_batch_size > 50000 THEN
        p_batch_size := 5000;
    END IF;

    WITH deleted_batch AS (
        DELETE FROM public.rate_limit_events
        WHERE id IN (
            SELECT id FROM public.rate_limit_events
            WHERE requested_at < v_cutoff
            ORDER BY requested_at ASC
            LIMIT p_batch_size
        )
        RETURNING id
    )
    SELECT COUNT(*)::INT INTO v_deleted FROM deleted_batch;

    RETURN v_deleted;
END;
$$;

REVOKE ALL ON FUNCTION public.cleanup_rate_limit_events(INT, INT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.cleanup_rate_limit_events(INT, INT) FROM anon, authenticated;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'service_role') THEN
        GRANT EXECUTE ON FUNCTION public.cleanup_rate_limit_events(INT, INT) TO service_role;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'postgres') THEN
        GRANT EXECUTE ON FUNCTION public.cleanup_rate_limit_events(INT, INT) TO postgres;
    END IF;
END $$;
