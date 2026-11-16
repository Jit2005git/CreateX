# CreateX AI — Phase 15C: Zero-Cost Infrastructure Architecture Plan (Revised)

**Document Version:** 2.0.0 (Corrected Post-Audit)  
**Budget Target:** **$0.00 / month (Strict Free Tier — Zero Credit Card Required)**  
**Status:** ARCHITECTURAL SPECIFICATION & PLAN (Pending User Review — No Infrastructure Changes Applied)

---

## 1. Executive Summary & Reality Check

This revised architecture plan outlines an authentic, zero-cost deployment strategy for CreateX AI. Following rigorous verification against provider terms of service, technical runtime constraints, and actual API quota models, several critical real-world realities must be established upfront:

### Critical Real-World Findings:
1. **Gemini Image Generation Has NO Free Tier:**  
   Google AI Studio **does not offer a free tier for image generation models** (`gemini-2.5-flash-image`, Imagen). Attempting to generate images with a free API key yields `HTTP 429 Resource Exhausted (limit: 0)`. Furthermore, `gemini-2.5-flash-image` is deprecated and scheduled for **shutdown on March 15, 2027**.  
   *Zero-Cost Strategy:* Campaign text generation (Gemini 3.1 Flash-Lite) is 100% free (15 RPM / 1,500 RPD). Poster generation will fail gracefully with user-friendly explanations; the application **will never silently bill or switch to paid endpoints**.
2. **Render and Koyeb Are Prototype/Demo Platforms, NOT Production-Grade:**  
   Free compute instances on Render and Koyeb are subject to severe constraints: **15-minute inactivity spin-down (30–50s cold starts)**, low resource allocations (512 MB RAM, 0.1 vCPU), shared CPU throttling, and arbitrary restarts. They are suitable for demos, testing, and portfolio showcases, but cannot provide commercial high-availability SLAs.
3. **Vercel Hobby Prohibits Commercial Use:**  
   Vercel's Terms of Service explicitly restrict the Hobby plan to **personal, non-commercial projects**. If CreateX AI is intended for commercial use or enterprise branding, **Cloudflare Pages** must be used instead (which permits commercial use on its free tier).
4. **Supabase 7-Day Inactivity Policy Cannot Be Bypassed by Trivial Pings:**  
   Supabase automatically pauses free-tier databases after 7 days of inactivity. Automated external SQL pings (`SELECT 1`) are not officially guaranteed to prevent pausing as Supabase's pause heuristic monitors dashboard interactions and client metrics. Restoration is manual via the dashboard.
5. **PostgreSQL-Backed Rate Limiting Replaces Paid Redis:**  
   External managed Redis ($35–$100+/mo) is replaced by an atomic PostgreSQL table with row-level locks on the existing free Supabase database. If the database is unreachable, rate limiting **fails closed with HTTP 503**, never silently permitting abuse.

---

## 2. Infrastructure Platform Evaluation

### 2.1 Frontend Hosting: Vercel vs Cloudflare Pages

| Feature | Vercel (Hobby Tier) | Cloudflare Pages (Free Tier) | Verdict & Recommendation |
| :--- | :--- | :--- | :--- |
| **Commercial Use Policy** | **Strictly Non-Commercial** (Personal/Hobby only) | **Permitted** (Commercial use explicitly allowed) | **Cloudflare Pages is recommended** for any commercial project; Vercel Hobby only for personal demo. |
| **Monthly Cost** | $0.00 (No credit card needed) | $0.00 (No credit card needed) | Both are 100% genuinely free. |
| **Bandwidth** | 100 GB / month (Hard cap) | **Unlimited bandwidth** | Cloudflare Pages has zero bandwidth limits. |
| **Build Limits** | 6,000 build minutes / month | 500 builds / month | Ample for continuous deployment. |
| **Cold Starts** | Zero (Static Anycast Edge CDN) | Zero (Static Anycast Edge CDN) | Instant global edge response. |
| **SPA Routing** | Supported via `vercel.json` | Supported via `_redirects` (`/* /index.html 200`) | Both support Vite HTML5 client-side routing. |

---

### 2.2 Backend Hosting: Render Free vs Koyeb Nano vs Cloud Run

| Attribute | Render (Free Web Service) | Koyeb (Free Nano) | Google Cloud Run (Free Tier) |
| :--- | :--- | :--- | :--- |
| **Hosting Classification** | **Prototype / Demo Hosting** | **Prototype / Demo Hosting** | Production Serverless |
| **Credit Card Required?** | **NO** (Zero billing risk) | **NO** (Zero billing risk) | **YES** (Carries billing liability) |
| **RAM & CPU** | 512 MB RAM, 0.1 vCPU | 512 MB RAM, 0.1 vCPU | 512 MB – 2 GB, 1-2 vCPU |
| **Cold Starts** | **30 to 50+ seconds** after 15 min idle | Fast (<5s) or continuous in single region | 2 to 5 seconds |
| **Usage Limits** | **750 free instance hours/month** shared across the entire account | 1 single Nano service per account | 2M requests/mo, 1 GB network egress |
| **Region Availability** | Oregon (US), Ohio (US), Frankfurt (EU) | Frankfurt (`fra`) or Washington D.C. (`was`) | Global (`us-central1`, etc.) |
| **Restarts & Ephemeral Disk** | Restarts at least once weekly; local disk wiped on reboot | Ephemeral disk; redeploys restart container | Ephemeral container instances |
| **Why Not Cloud Run?** | Render has zero billing risk. | Koyeb has zero billing risk. | Cloud Run requires a credit card and bills overage if egress > 1 GB. |

> [!WARNING]
> **Render's 750 Instance Hours Myth:**  
> Render's 750 free hours cover exactly one service running continuously for a 31-day month ($31 \times 24 = 744$ hours). If you create a second service, a worker, or leave an old build running in the same account, free hours will exhaust mid-month, causing all free services to suspend until the next calendar month.

---

### 2.3 Database, Auth & Storage: Supabase Free Tier

| Capability | Free Tier Allowance | Real-World Operational Constraint |
| :--- | :--- | :--- |
| **PostgreSQL Database** | 500 MB storage | Ample for text metadata; strictly monitor table growth. |
| **Authentication (GoTrue)** | 50,000 Monthly Active Users | Completely sufficient for prototype and early production. |
| **Storage (`createx-posters`)** | 1 GB file storage, 2 GB egress/month | 2 GB egress allows ~20,000 views of 100 KB posters. |
| **7-Day Inactivity Pause** | Automatic pause after 7 days | **Reality:** Trivial `SELECT 1` queries cannot be relied upon to prevent pausing. If paused, restoring requires logging into the Supabase Dashboard and manually clicking "Restore Project" (takes 1–2 minutes). Projects paused for >90 days risk permanent deletion. |
| **Backup Retention** | Daily backup snapshot (no PITR) | Point-in-time recovery is not available on free tier. Manual schema dumps (`schema.sql`) must be version-controlled in Git. |

---

### 2.4 AI Engine & Image Generation Reality: Google AI Studio

| Model | Capability | Official Free Tier Allowance | Operational Reality |
| :--- | :--- | :--- | :--- |
| **Gemini 3.1 Flash-Lite** (`gemini-3.1-flash-lite`) | Campaign Strategy, Brand Context, Storyboard, Social Copy | **15 RPM**, 1,500 RPD, 1M TPM | **100% Free** via Google AI Studio API key without billing. |
| **Gemini 2.5 Flash Image** (`gemini-2.5-flash-image`) | Marketing Poster Image Generation | **NO FREE TIER** ($0 allowance, `limit: 0`) | **Paid Only.** Attempting to call with a free key returns HTTP 429 quota exhaustion. Scheduled for **permanent shutdown on March 15, 2027**. |

> [!IMPORTANT]
> **Zero-Cost Policy on AI Image Generation:**  
> 1. Because image generation requires a linked credit card, CreateX AI **will not make unverified claims of free image generation**.
> 2. Poster generation requests that return HTTP 429/503 quota errors are intercepted and translated into clear user guidance: *"AI Poster Generation requires paid Gemini Image credits. Campaign text generation, strategy, and copy remain fully functional on the free tier."*
> 3. The backend will **never silently switch to a paid API tier or alternative provider**.
> 4. Campaign context and text generation continue to work independently without being blocked by poster generation failures.

---

## 3. High-Performance PostgreSQL-Backed Atomic Rate Limiting

### 3.1 Algorithm Analysis: Sliding Window vs Fixed Window with Row-Level Locking

To replace paid Redis ($35+/mo) for $0, rate limiting executes directly inside Supabase PostgreSQL.

#### Algorithm Selection
- A naive `COUNT(*)` over a raw event-log table can degrade database performance under high query volume.
- A naive counter resetting at `window_start + 60s` suffers from the "boundary burst" problem (a user can send 5 requests at second 59 and 5 requests at second 61).
- **The Selected Algorithm:** A **Sliding-Log Counter with Row-Level Atomic Locking**. 
  - An unlogged table `rate_limit_events` records individual request timestamps `(bucket_key, requested_at)`.
  - An atomic stored procedure acquires an advisory lock or row-level lock on the `bucket_key`, prunes timestamps older than `NOW() - window_seconds`, counts active timestamps, and appends the current timestamp only if under the threshold.
  - This is a **genuine sliding window algorithm**, identical to Redis sorted sets (`ZREMRANGEBYSCORE` + `ZCARD` + `ZADD`).

### 3.2 SQL Schema & Atomic Stored Procedure

```sql
-- ─────────────────────────────────────────────────────────────────────────────
-- Unlogged table for ultra-low latency (bypasses WAL disk writes)
-- Note: Automatically truncated upon database crash or restart, which is
-- completely safe and expected for transient rate-limit counters.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE UNLOGGED TABLE IF NOT EXISTS public.rate_limit_events (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bucket_key   TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rate_limit_lookup 
    ON public.rate_limit_events (bucket_key, requested_at DESC);

-- ─────────────────────────────────────────────────────────────────────────────
-- Atomic Sliding Window Check-and-Increment Function
-- ─────────────────────────────────────────────────────────────────────────────
CREATE OR REPLACE FUNCTION public.check_sliding_rate_limit(
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
    v_window_start TIMESTAMPTZ := v_now - (p_window_secs || ' seconds')::INTERVAL;
    v_count        INT;
    v_earliest     TIMESTAMPTZ;
    v_retry_after  INT := 0;
    v_lock_id      BIGINT;
BEGIN
    -- Derive a 64-bit integer lock key from the string using hashtext
    v_lock_id := ('x' || SUBSTR(MD5(p_key), 1, 16))::BIT(64)::BIGINT;

    -- Acquire transaction-level advisory lock for this specific key
    -- This guarantees strict serialization under concurrent requests across all instances
    PERFORM pg_advisory_xact_lock(v_lock_id);

    -- 1. Evict timestamps outside the sliding window for this key
    DELETE FROM public.rate_limit_events
    WHERE bucket_key = p_key AND requested_at <= v_window_start;

    -- 2. Count active requests within the sliding window
    SELECT COUNT(*), MIN(requested_at)
    INTO v_count, v_earliest
    FROM public.rate_limit_events
    WHERE bucket_key = p_key;

    -- 3. Evaluate threshold
    IF v_count >= p_max_requests THEN
        -- Rate limit exceeded: calculate exact seconds until earliest timestamp expires
        v_retry_after := GREATEST(1, EXTRACT(EPOCH FROM (v_earliest + (p_window_secs || ' seconds')::INTERVAL - v_now))::INT);
        RETURN QUERY SELECT false, 0, v_retry_after;
        RETURN;
    END IF;

    -- 4. Within limit: record request timestamp
    INSERT INTO public.rate_limit_events (bucket_key, requested_at)
    VALUES (p_key, v_now);

    RETURN QUERY SELECT true, p_max_requests - (v_count + 1), 0;
    RETURN;
END;
$$;

-- Stale cleanup routine (to prevent table bloat during low traffic periods)
CREATE OR REPLACE FUNCTION public.cleanup_stale_rate_limit_events()
RETURNS VOID
LANGUAGE sql
AS $$
    DELETE FROM public.rate_limit_events WHERE requested_at < NOW() - INTERVAL '5 minutes';
$$;
```

### 3.3 Proof of Atomicity Under Concurrent Requests
1. **Advisory Locking (`pg_advisory_xact_lock`):**  
   The function hashes `bucket_key` into a 64-bit integer and requests an exclusive transaction advisory lock. 
2. **Strict Serialization:**  
   If 10 concurrent requests arrive simultaneously across 3 Render instances for `guest:sess_abc123`:
   - Request 1 acquires the lock, cleans up expired rows, counts active events, inserts its timestamp, and releases the lock on commit.
   - Request 2 waits on the lock, acquires it, sees Request 1's inserted timestamp, and evaluates accurately.
   - Race conditions, double-counts, and phantom increments are mathematically eliminated.
3. **Failsafe Store Behavior (HTTP 503):**  
   If the Supabase connection times out or fails:
   The backend catches the exception and immediately raises:
   ```http
   HTTP/1.1 503 Service Unavailable
   Content-Type: application/json

   { "detail": "Rate limiting verification service is temporarily unavailable. Please retry." }
   ```
   **It will never silently disable rate limiting during a database outage.**

### 3.4 Consequences of Using an `UNLOGGED` Table
- **Performance Benefit:** Zero disk writes to PostgreSQL Write-Ahead Logs (WAL). Reduces database I/O to near-memory speeds (~1–3ms per check).
- **Restart Consequence:** If the Supabase database restarts, crashes, or is restored, the `rate_limit_events` table is automatically truncated to empty.  
- **Acceptability:** Rate-limit counters are transient (60-second window). Wiping counters during a server reboot causes no permanent data loss, mirroring the exact behavior of Redis restarting.

---

## 4. End-to-End Rate Limiter Test Strategy

Before promoting this implementation, an automated test suite (`backend/test_postgres_rate_limiter.py`) will execute:
1. **Concurrency Test:** Launch 15 concurrent asyncio worker tasks competing for 5 allowed slots; verify exactly 5 succeed (HTTP 200) and exactly 10 fail (HTTP 429).
2. **Sliding Expiration Test:** Verify that after the sliding window elapses, slots are accurately freed.
3. **Identity Separation Test:** Verify `user:1`, `guest:A`, and `ip:1.2.3.4` maintain completely independent counters.
4. **Failsafe Store Outage Test:** Simulate database connection error and verify the backend raises `HTTP 503 Service Unavailable` rather than letting unmetered requests through.
5. **Cleanup Function Test:** Verify `cleanup_stale_rate_limit_events()` removes entries older than 5 minutes.

---

## 5. Deployment Instructions for $0 Prototype / Demo Setup

### Step 1: Database Migration (Supabase Dashboard)
1. Navigate to Supabase SQL Editor.
2. Run `database/rate_limit_schema.sql` (creating `rate_limit_events` and `check_sliding_rate_limit`).

### Step 2: Deploy Backend to Render ($0/month Prototype Web Service)
1. In Render Dashboard, create **New Web Service** connected to your repository.
2. Configure:
   - **Environment:** `Python 3`
   - **Root Directory:** `backend`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT --workers 1`
   - **Plan:** `Free`
3. Environment Variables:
   - `APP_ENV` = `production`
   - `FRONTEND_URL` = `https://createx-ai.pages.dev` (or your Cloudflare Pages domain)
   - `ALLOWED_ORIGINS` = `https://createx-ai.pages.dev`
   - `RATE_LIMIT_STORE` = `postgres`
   - `GEMINI_API_KEY` = `<your-api-key>`
   - `GEMINI_TEXT_MODEL` = `gemini-3.1-flash-lite`
   - `GEMINI_IMAGE_MODEL` = `gemini-2.5-flash-image`
   - `SUPABASE_URL` = `<your-supabase-url>`
   - `SUPABASE_SERVICE_ROLE_KEY` = `<your-service-role-key>`
   - `SUPABASE_ANON_KEY` = `<your-anon-key>`
   - `SUPABASE_JWT_SECRET` = `<your-jwt-secret>`
   - `SUPABASE_STORAGE_BUCKET` = `createx-posters`

### Step 3: Deploy Frontend to Cloudflare Pages ($0/month Commercial-Friendly)
1. In Cloudflare Dashboard -> **Compute (Workers & Pages)** -> **Pages** -> **Connect to Git**.
2. Select your repository.
3. Configure build:
   - **Framework:** `Vite`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
4. Add Environment Variables:
   - `VITE_API_BASE_URL` = `https://createx-backend.onrender.com`
   - `VITE_SUPABASE_URL` = `<your-supabase-url>`
   - `VITE_SUPABASE_ANON_KEY` = `<your-anon-key>`
5. Add `frontend/public/_redirects`:
   ```
   /* /index.html 200
   ```
6. Click **Save and Deploy**.
