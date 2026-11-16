# CreateX AI — Phase 15D: PostgreSQL Atomic Rate Limiter Implementation Report

**Document Version:** 1.0.0  
**Date:** 2026-11-17  
**Status:** Completed & Verified  
**Infrastructure Cost Impact:** $0.00/month (Leverages existing Supabase PostgreSQL instance)

---

## 1. Executive Summary

As part of CreateX AI's **strict $0/month zero-cost infrastructure plan** (detailed in `docs/PHASE15C_ZERO_COST_ARCHITECTURE.md`), Phase 15D replaces external paid Redis instances (e.g., Upstash paid tiers or self-hosted Redis VMs) with an atomic, high-performance sliding-log rate limiter directly in PostgreSQL.

By utilizing PostgreSQL transaction-level advisory locks (`pg_advisory_xact_lock`) and an `UNLOGGED` transient event table, the implementation achieves:
1. **Full Atomicity:** Eliminates race conditions across concurrent requests competing for the same quota slot without table-wide locking.
2. **Zero WAL Overhead:** The table is unlogged, avoiding disk write-ahead log amplification and preserving Supabase free-tier database IOPS and bandwidth.
3. **No Phantom Rejections:** Requests exceeding the quota do not record event rows, preventing artificial lock-out extension.
4. **Strict Isolation:** Preserves independent rate-limiting buckets for authenticated user IDs, guest session IDs, and client IP addresses.
5. **Fail-Closed Resilience:** If the database becomes unreachable, the backend fails closed with `HTTP 503 Service Unavailable`, preventing unmetered bypass during outages.
6. **Defensive Security:** The table and functions are completely revoked from `PUBLIC`, `anon`, and `authenticated` roles, accessible strictly via `service_role`.

---

## 2. Architecture & Database Design

### 2.1 Schema Definition (`public.rate_limit_events`)

The schema is defined in [database/migrations/20261117_001_rate_limit_events.sql](file:///d:/projects/CreateX/CreateX/database/migrations/20261117_001_rate_limit_events.sql):

```sql
CREATE UNLOGGED TABLE IF NOT EXISTS public.rate_limit_events (
    id           BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    bucket_key   TEXT NOT NULL,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Compound index supporting rapid range counts within sliding window
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_lookup
    ON public.rate_limit_events (bucket_key, requested_at DESC);

-- Index supporting bounded batch cleanup of expired events
CREATE INDEX IF NOT EXISTS idx_rate_limit_events_cleanup
    ON public.rate_limit_events (requested_at);
```

#### Key Architectural Properties:
- **`UNLOGGED` Table:** High write-throughput rate-limiting records bypass WAL (Write-Ahead Logging). Writes are fast and transient.
- **Restart Behavior:** If the PostgreSQL server crashes or restarts, unlogged tables are automatically truncated to an empty state. Because rate-limit windows are short (typically 60 seconds), resetting rate-limit state on rare server restarts is safe, self-healing, and preferable to accumulating bloated WAL logs.
- **Timestamping:** Uses `clock_timestamp()` rather than `CURRENT_TIMESTAMP` or `NOW()` to ensure monotonic real-time timestamps even within concurrent sub-statements of long transactions.

---

## 3. Concurrency & Atomicity Mechanism

### 3.1 Advisory Lock Serialization (`pg_advisory_xact_lock`)

The core challenge of database rate limiters is avoiding race conditions (time-of-check to time-of-use) without locking the whole table. Phase 15D solves this with deterministic 64-bit integer hashing for PostgreSQL advisory locks:

```sql
-- Compute deterministic 64-bit signed bigint lock id from the bucket key
v_lock_id := ('x' || SUBSTR(MD5(p_key), 1, 16))::BIT(64)::BIGINT;

-- Acquire transaction-level exclusive advisory lock
PERFORM pg_advisory_xact_lock(v_lock_id);
```

### 3.2 Algorithm Flow (`check_rate_limit`)

```mermaid
flowchart TD
    A[Incoming Request] --> B[Generate Bucket Key: e.g. campaign:guest:sess_xyz]
    B --> C[Compute 64-bit Hash of Bucket Key]
    C --> D[pg_advisory_xact_lock: Wait for/Acquire Bucket Lock]
    D --> E[Count Events where bucket_key = p_key AND requested_at > window_start]
    E --> F{Current Count < Max Requests?}
    F -- Yes (Allowed) --> G[INSERT INTO rate_limit_events]
    G --> H[Return allowed=true, remaining, retry_after=0]
    H --> K[Commit Transaction: Advisory Lock Automatically Released]
    F -- No (Rejected) --> I[DO NOT INSERT EVENT]
    I --> J[Return allowed=false, remaining=0, retry_after=secs]
    J --> K
```

### 3.3 Protection Against Over-Counting (No Rejected Inserts)
A critical requirement is that requests rejected with `HTTP 429` must **not** insert an event row. Inserting rows on rejection creates an artificial avalanche where a user who continues sending requests remains blocked indefinitely long past their original window. The function ensures rejected requests only read the count and return the remaining retry duration without writing to storage.

---

## 4. Security & Role Hardening

| Security Aspect | Implementation Detail | Protection Mechanism |
|---|---|---|
| **Role Restriction** | `REVOKE ALL ON public.rate_limit_events FROM PUBLIC, anon, authenticated;` | Prevents malicious frontend clients or compromised user tokens from reading or clearing rate limits. |
| **Execution Privilege** | `GRANT EXECUTE ON FUNCTION public.check_rate_limit TO service_role;` | Accessible exclusively by the backend FastAPI service role. |
| **Search Path Hardening** | `SECURITY DEFINER SET search_path = public, pg_catalog, pg_temp;` | Protects against schema substitution and search-path hijacking attacks in PostgreSQL. |
| **Input Validation** | Explicit validation on key length (1-256 chars), max_requests (1-10000), and window_secs (1-86400). | Raises SQL `invalid_parameter_value` on malformed inputs. |
| **Advisory Lock Scope** | Transaction-level (`xact`) lock | Automatically released on transaction end or failure, preventing orphaned locks. |

---

## 5. Maintenance & Pruning Runbook

To prevent table growth over time, a bounded maintenance procedure is provided:

```sql
CREATE OR REPLACE FUNCTION public.cleanup_rate_limit_events(
    p_retention_secs INT DEFAULT 300,
    p_batch_size INT DEFAULT 5000
) RETURNS INT ...
```

### 5.1 Operational Characteristics:
- **Default Retention:** 300 seconds (5 minutes), clamped to >= 60 seconds. Safe for 60-second rate-limit windows.
- **Bounded Deletion:** Deletes records in chunks of `p_batch_size` (default: 5,000, max: 50,000) using `LIMIT` on a subquery of `id`s. This prevents long table locks or transaction buffer exhaustion.
- **Execution Options ($0/month):**
  1. **Supabase `pg_cron` extension (Free):**
     ```sql
     SELECT cron.schedule('prune-rate-limits', '*/30 * * * *', 'SELECT public.cleanup_rate_limit_events(300, 5000)');
     ```
  2. **FastAPI Background Worker / Lifespan Task:**
     An `asyncio` task calling `cleanup_rate_limit_events` every hour via the existing backend service client.

---

## 6. Backend Integration

The backend in [backend/app/core/rate_limiter.py](file:///d:/projects/CreateX/CreateX/backend/app/core/rate_limiter.py) incorporates the `PostgresRateLimitStore`:

1. **Environment Flag:** Enabled by setting `RATE_LIMIT_STORE=postgres` (defaults to `memory` in development, supports `redis` or `postgres` in production).
2. **Deterministic Invocation:** Calls Supabase RPC `check_rate_limit` with `p_key`, `p_max_requests`, and `p_window_secs`.
3. **Fail-Closed Behavior:** If the PostgreSQL RPC call encounters network failure or database errors, it raises `RateLimitStoreUnavailableError`, which the endpoint handler translates into `HTTP 503 Service Unavailable`.
4. **Header Spoofing Hardening:** `_get_client_ip` uses Python's `ipaddress` module to parse and validate client IPs, falling back safely to the socket IP if headers are untrusted or malformed.

---

## 7. Verification Test Suite Results

The verification suite in [backend/test_postgres_rate_limiter.py](file:///d:/projects/CreateX/CreateX/backend/test_postgres_rate_limiter.py) validates all aspects of concurrency, sliding expiration, security, and migration scripts.

### Test Execution Summary

```
======================================================================
  CreateX AI - PostgreSQL Atomic Rate Limiter Verification Suite
======================================================================

--- Part 1: Concurrency, Sliding Expiration & Store Resilience ---
  [PASS] [Concurrency] 10 concurrent requests for 3 slots -> exactly 3 succeed, 7 receive 429 -> 200_ok=3, 429_limited=7
  [PASS] [Correctness] Rejected requests do NOT insert events into storage -> recorded_events=3 (expected exactly 3)
  [PASS] [SlidingWindow] Requests become eligible again after sliding window expires -> initial_blocked=True, eligible_after_window=True
  [PASS] [IdentityIsolation] Authenticated users have independent rate-limit buckets -> user_a_limited=True, user_b_allowed=True
  [PASS] [IdentityIsolation] Guest sessions have independent rate-limit buckets -> g1_limited=True, g2_allowed=True
  [PASS] [Security] Untrusted/malformed X-Forwarded-For headers rejected; falls back to socket IP -> extracted_ip=192.168.1.100
  [PASS] [Failsafe] Database failure returns HTTP 503 Service Unavailable (Fail Closed) -> status=503, detail=Rate limiting verification service is temporarily unavailable. Please retry.
  [PASS] [Maintenance] Cleanup removes expired events without deleting active events -> deleted=5, remaining_active=2

--- Part 2: SQL Migration Static Security & Schema Audit ---
  [PASS] [SQLAudit] Advisory lock (pg_advisory_xact_lock) present in stored procedure
  [PASS] [SQLAudit] Table defined as UNLOGGED for zero-WAL memory-speed execution
  [PASS] [SQLAudit] Permissions explicitly revoked from PUBLIC, anon, authenticated
  [PASS] [SQLAudit] Execution granted strictly to service_role
  [PASS] [SQLAudit] Function uses SECURITY DEFINER with fixed search_path (hijack protection)
  [PASS] [SQLAudit] Bounded cleanup function with batch deletion limit implemented

--- Part 3: Real Database Live Integration Check ---
  [SKIPPED] [LiveDB] check_rate_limit live execution -> Migration not applied to production Supabase (in accordance with user instruction)

======================================================================
  Rate Limiter Results: 14 passed, 0 failed, 1 skipped
======================================================================
```

### Full Regression Suite Results
In addition to the rate limiter verification, all existing project suites were run and passed 100%:
- **Phase 14B Security Remediation:** 22/22 passed (Zero bypass, mock token rejection, HTTP 429 enforcement).
- **Supabase Security Suite:** 18/18 passed (Token validation, guest session boundary, project access isolation).
- **Phase 13 Image Storage Suite:** 17/17 passed (Real PNG/JPEG/WebP storage, CDN retrieval, SHA256 integrity, tenant isolation).
- **Frontend Authentication Suite:** 8/8 passed (Session cache, token management, header assembly, 401 handling).

**Total Verified Checks:** 79 passed, 0 failed.

---

## 8. Migration & Rollback Runbook

> [!IMPORTANT]
> In accordance with safety instructions, the migration has **not** been applied to the live production database. When the deployment team is ready to apply it, follow the steps below.

### 8.1 Applying the Migration

**File:** [database/migrations/20261117_001_rate_limit_events.sql](file:///d:/projects/CreateX/CreateX/database/migrations/20261117_001_rate_limit_events.sql)

**Via Supabase Dashboard SQL Editor:**
1. Navigate to the Supabase Project Dashboard -> **SQL Editor**.
2. Paste the contents of `database/migrations/20261117_001_rate_limit_events.sql`.
3. Click **Run**.
4. Verify execution output reports `Success. No rows returned`.

**Via Supabase CLI / `psql`:**
```bash
psql "$DATABASE_URL" -f database/migrations/20261117_001_rate_limit_events.sql
```

### 8.2 Enabling in FastAPI Backend

Once the migration is applied in the database:
1. Set the following environment variable in the backend environment (e.g. Render dashboard or `.env`):
   ```env
   RATE_LIMIT_STORE=postgres
   ```
2. Restart the backend service.

### 8.3 Rollback Procedure

**File:** [database/migrations/20261117_001_rate_limit_events_rollback.sql](file:///d:/projects/CreateX/CreateX/database/migrations/20261117_001_rate_limit_events_rollback.sql)

If rolling back is required:
1. Revert backend environment variable to `RATE_LIMIT_STORE=memory` (or `redis`) and restart backend.
2. Run the rollback script in Supabase SQL Editor:
   ```sql
   DROP FUNCTION IF EXISTS public.cleanup_rate_limit_events(INT, INT);
   DROP FUNCTION IF EXISTS public.check_rate_limit(TEXT, INT, INT);
   DROP TABLE IF EXISTS public.rate_limit_events;
   ```

---

## 9. Safe Test-Only Migration & Rollback Runbook (Phase 15D.2)

To ensure zero risk to existing production databases and strict validation prior to any live usage, follow this test-only operational sequence:

```mermaid
flowchart TD
    S1[1. Isolation Confirmation] --> S2[2. Apply Migration to Test DB]
    S2 --> S3[3. Schema & Privilege Inspection]
    S3 --> S4[4. Real Multi-Connection Integration Tests]
    S4 --> S5[5. Pruning & Retention Verification]
    S5 --> S6[6. Apply Rollback Migration]
    S6 --> S7[7. Verify Clean Teardown: Zero Orphaned Objects]
```

### Step 1: Isolation Confirmation
Confirm the target database is an isolated local or development database with zero production data:
```bash
# Verify connection string targets test/development database, NOT production
echo "$TEST_DATABASE_URL"
```

### Step 2: Apply Forward Migration
Apply `database/migrations/20261117_001_rate_limit_events.sql`:
```bash
psql "$TEST_DATABASE_URL" -f database/migrations/20261117_001_rate_limit_events.sql
```

### Step 3: Inspect Schema, Indices, and Grants
Verify created database objects and privilege revocations:
```sql
-- 1. Verify UNLOGGED table and columns
\d+ public.rate_limit_events;

-- 2. Verify indexes exist
\di public.idx_rate_limit_events_*;

-- 3. Verify execution permissions (must return only service_role and postgres)
SELECT routine_name, grantee, privilege_type
FROM information_schema.routine_privileges
WHERE routine_schema = 'public' AND routine_name IN ('check_rate_limit', 'cleanup_rate_limit_events');

-- 4. Verify table privileges (PUBLIC, anon, authenticated must NOT have access)
SELECT table_name, grantee, privilege_type
FROM information_schema.table_privileges
WHERE table_schema = 'public' AND table_name = 'rate_limit_events';
```

### Step 4: Run Real PostgreSQL Integration Tests
Execute the independent connection integration suite:
```bash
TEST_DATABASE_URL="$TEST_DATABASE_URL" python backend/test_postgres_rate_limiter_real.py
```

### Step 5: Verify Bounded Pruning
Confirm the cleanup function works on expired records:
```sql
SELECT public.cleanup_rate_limit_events(60, 1000);
```

### Step 6: Apply Rollback Migration
Apply `database/migrations/20261117_001_rate_limit_events_rollback.sql`:
```bash
psql "$TEST_DATABASE_URL" -f database/migrations/20261117_001_rate_limit_events_rollback.sql
```

### Step 7: Confirm Only Phase 15D Objects Were Removed
Verify complete, clean removal of Phase 15D objects without touching existing application tables:
```sql
-- All three must return 0 rows
SELECT 1 FROM pg_tables WHERE schemaname = 'public' AND tablename = 'rate_limit_events';
SELECT 1 FROM pg_proc WHERE proname IN ('check_rate_limit', 'cleanup_rate_limit_events');

-- Verify existing application tables remain completely intact
SELECT tablename FROM pg_tables WHERE schemaname = 'public';
-- Expected: projects, generated_assets, profiles, etc.
```
