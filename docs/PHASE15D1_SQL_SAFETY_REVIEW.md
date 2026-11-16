# CreateX AI — Phase 15D.1: Pre-Migration SQL Safety Review

**Document Version:** 1.0.0  
**Audit Date:** 2026-11-17  
**Scope:** Review of PostgreSQL Rate Limiter Migration, Rollback, Backend Integration, Test Harness, and Documentation.  
**Reviewed Files:**
- `database/migrations/20261117_001_rate_limit_events.sql`
- `database/migrations/20261117_001_rate_limit_events_rollback.sql`
- `backend/app/core/rate_limiter.py`
- `backend/test_postgres_rate_limiter.py`
- `docs/PHASE15D_RATE_LIMITER_REPORT.md`

**Status:** Complete  
**Final Recommendation:** **SAFE TO APPLY TO A TEST DATABASE**

---

## 1. Executive Summary of Audit Results

All 12 security and architectural safety checks were evaluated against the source code. 

- **10 Checks PASSED:** The SQL migration scripts exhibit strict role isolation, transaction-level advisory lock atomicity, fail-closed design, safe parameter validation, unlogged memory-speed performance, and non-destructive rollback semantics.
- **2 Checks NEED ATTENTION:** 
  1. *Check 7 (Client IP Extraction):* Header sanitization validates IPv4/IPv6 syntax but does not restrict parsing to verified upstream proxy IPs.
  2. *Check 10 (Concurrency Test):* Concurrency testing in `test_postgres_rate_limiter.py` is an in-memory simulation (`SimulatedPostgresStore` with `asyncio.Lock`), not a physical multi-connection database test.
- **Documentation Erratum:** Column names in the report snippet (`key`, `created_at`) differed slightly from the actual SQL schema (`bucket_key`, `requested_at`), though the actual migration script and backend code are 100% aligned.

---

## 2. Detailed Checklist Evaluation

### Check 1: Advisory Lock Serialization within Transaction
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L87-L118`  
**Analysis:**
The stored procedure `public.check_rate_limit` derives a 64-bit integer lock key and executes `PERFORM pg_advisory_xact_lock(v_lock_id)` at line 92. This occurs:
1. **Before** pruning expired entries (`DELETE ... WHERE bucket_key = p_key AND requested_at <= v_window_start` at line 95).
2. **Before** counting active requests (`SELECT COUNT(*), MIN(requested_at) ... WHERE bucket_key = p_key` at line 99).
3. **Before** inserting the new request timestamp (`INSERT INTO public.rate_limit_events ...` at line 114).

Because `pg_advisory_xact_lock` is transaction-scoped (`xact`), PostgreSQL holds the exclusive lock on this specific bucket until the transaction commits or rolls back, serializing concurrent requests sharing that bucket.

---

### Check 2: Deterministic Lock Key & Quota Collision Isolation
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L88`, `L95-L102`, `L114-L115`; `backend/app/core/rate_limiter.py#L360-L364`, `L392-L395`  
**Analysis:**
- **Lock Key Derivation:** `v_lock_id := ('x' || SUBSTR(MD5(p_key), 1, 16))::BIT(64)::BIGINT;` deterministically converts the bucket string into a 64-bit integer across all PostgreSQL versions.
- **Quota Separation Under Advisory Collisions:** In the rare event of a 64-bit advisory lock hash collision ($1 \text{ in } 2^{64}$), two distinct keys would briefly serialize execution (one waits fractions of a millisecond for the other's transaction to end). Crucially, **their quotas and counters never merge** because all queries (`DELETE`, `SELECT COUNT(*)`, and `INSERT`) filter strictly by the full literal string `WHERE bucket_key = p_key`.
- **Bucket Namespace:** In `rate_limiter.py`, the key incorporates both the endpoint domain and identity (`campaign:user:<id>`, `campaign:guest:<session_id>`, `campaign:ip:<ip>`), preventing cross-endpoint collisions.

---

### Check 3: Transaction Isolation & Visibility After Lock Wait
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L90-L103`  
**Analysis:**
- Standard Supabase/PostgREST RPC calls execute under PostgreSQL's default `READ COMMITTED` isolation level.
- When Request 2 blocks on `pg_advisory_xact_lock(v_lock_id)` waiting for Request 1 to complete, Request 2 remains halted at line 92.
- Under `READ COMMITTED`, every individual SQL statement acquires a fresh snapshot of the database state. When Request 1 commits and releases the lock, Request 2 unblocks and executes statement 4 (`DELETE`) and statement 5 (`SELECT COUNT(*)`).
- Consequently, Request 2's snapshot is instantiated **after** Request 1 has committed, ensuring Request 2 sees Request 1's newly committed row.

---

### Check 4: Rejected Requests Event Invariant & `Retry-After` Calculation
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L104-L111`; `backend/app/core/rate_limiter.py#L379-L383`  
**Analysis:**
- When `v_count >= p_max_requests` (line 105), the procedure calculates `v_retry_after := GREATEST(1, EXTRACT(EPOCH FROM (v_earliest + (p_window_secs || ' seconds')::INTERVAL - v_now))::INT);` and executes `RETURN QUERY SELECT false, 0, v_retry_after; RETURN;`.
- **No rows are inserted on rejection.** The `INSERT` statement (line 114) is unreachable when the limit is exceeded. This eliminates the "avalanche lockout" failure mode where repeated rejections prolong the block duration.
- `GREATEST(1, ...)` ensures that even with sub-second expiration windows, `Retry-After` is at least 1 integer second in compliance with RFC 7231.
- In `backend/app/core/rate_limiter.py`, `HTTPException(status_code=429)` cleanly attaches `headers={"Retry-After": str(retry_after)}`.

---

### Check 5: `SECURITY DEFINER` Search Path & Object Schema Qualification
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L60-L63`, `L95`, `L101`, `L114`, `L143-L146`, `L160-L162`  
**Analysis:**
- Both `check_rate_limit` (lines 61-62) and `cleanup_rate_limit_events` (lines 144-145) explicitly specify:
  ```sql
  SECURITY DEFINER
  SET search_path = public, pg_temp
  ```
- All database objects inside the function bodies are fully qualified: `public.rate_limit_events`.
- This conforms to PostgreSQL secure coding standards, preventing search-path substitution or Trojan object injection by low-privileged database users.

---

### Check 6: Strict Role Restrictions & Least Privilege
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L33-L46`, `L122-L134`, `L175-L186`  
**Analysis:**
- **Table Permissions:**
  - `ALTER TABLE public.rate_limit_events ENABLE ROW LEVEL SECURITY;`
  - `REVOKE ALL ON TABLE public.rate_limit_events FROM PUBLIC;`
  - `REVOKE ALL ON TABLE public.rate_limit_events FROM anon, authenticated;`
  - `GRANT SELECT, INSERT, DELETE ON TABLE public.rate_limit_events TO service_role;`
- **RPC Function Permissions:**
  - `REVOKE ALL ON FUNCTION public.check_rate_limit FROM PUBLIC;`
  - `REVOKE EXECUTE ON FUNCTION public.check_rate_limit FROM anon, authenticated;`
  - `GRANT EXECUTE ON FUNCTION public.check_rate_limit TO service_role;`
- Anonymous browsers (`anon`) and logged-in users (`authenticated`) cannot query, modify, or reset rate limit records directly via PostgREST. Only the backend FastAPI server holding the `service_role` key can invoke the RPC.

---

### Check 7: Client IP Extraction & Untrusted Proxy Headers
**Status:** **NEEDS ATTENTION**  
**File & Lines:** `backend/app/core/rate_limiter.py#L300-L325`  
**Severity:** Medium-High (Abuse mitigation)  
**Analysis:**
```python
forwarded = request.headers.get("X-Forwarded-For")
if forwarded:
    candidate = forwarded.split(",")[0].strip()
    try:
        ipaddress.ip_address(candidate)
        return candidate
    except ValueError:
        pass
```
- **Strengths:** The code validates that `candidate` is syntactically a valid IPv4 or IPv6 address, preventing SQL/script injection via headers.
- **Vulnerability:** The code trusts `X-Forwarded-For` unconditionally without verifying whether the direct socket peer (`request.client.host`) is a trusted reverse proxy (e.g. Render proxy, Cloudflare IP ranges, or `127.0.0.1`).
- **Impact:** An attacker who knows the server's public endpoint can forge `X-Forwarded-For: 203.0.113.X` with varying valid IPs on each request, bypassing the supplementary IP rate limit (`rate_limit_campaign_ip_per_minute`).
- **Mitigating Factor:** Primary identity rate limits (`user:<id>` or `guest:<session_id>`) remain enforced independently and cannot be bypassed via IP spoofing.
- **Required Fix:** Check `request.client.host` against a configured `TRUSTED_PROXIES` whitelist before honoring `X-Forwarded-For`, or configure Uvicorn's native `--proxy-headers` / `--forwarded-allow-ips`.

---

### Check 8: Bounded Cleanup, Indexing & Window Retention
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L29-L30`, `L138-L173`  
**Analysis:**
- **Index Support:** Line 29 creates `CREATE INDEX IF NOT EXISTS idx_rate_limit_events_cleanup ON public.rate_limit_events (requested_at);`.
- **Bounded Batches:** The cleanup function `cleanup_rate_limit_events` enforces safe bounds:
  - `p_batch_size` is clamped between 1 and 50,000 (default 5,000).
  - Uses `WHERE id IN (SELECT id FROM ... WHERE requested_at < v_cutoff ORDER BY requested_at ASC LIMIT p_batch_size)` to prevent long lock contention on large tables.
- **Window Safety:** `p_retention_secs` is clamped to $\ge 60$ seconds (defaults to 300s / 5 minutes). This is well beyond the active application sliding window (60s), ensuring active rate-limit buckets are never pruned prematurely.
- **Inline Bucket Pruning:** Furthermore, `check_rate_limit` automatically cleans expired records for active keys at line 95 during normal traffic.

---

### Check 9: Fail-Closed Behavior & Silent Fallback Prevention
**Status:** **PASS**  
**File & Lines:** `backend/app/core/rate_limiter.py#L107-L110`, `L365-L370`, `L397-L402`  
**Analysis:**
- In `PostgresRateLimitStore`:
  ```python
  except Exception as e:
      logger.error("PostgreSQL rate limit store error for key %s: %s", key, e)
      raise RateLimitStoreUnavailableError(...) from e
  ```
  It does **not** fall back to in-memory storage when PostgreSQL fails.
- In `RateLimiter.__call__`:
  ```python
  except RateLimitStoreUnavailableError as e:
      raise HTTPException(
          status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
          detail="Rate limiting verification service is temporarily unavailable. Please retry."
      )
  ```
- If the database goes offline or credentials become invalid, the backend fails closed with `HTTP 503`. Unmetered requests are strictly rejected.

---

### Check 10: Concurrency Test Harness & Live Synchronization
**Status:** **NEEDS ATTENTION**  
**File & Lines:** `backend/test_postgres_rate_limiter.py#L96-L198`, `L399-L430`  
**Severity:** Medium (Verification rigor)  
**Analysis:**
- **Observation:** In `test_postgres_rate_limiter.py`, Part 1 concurrency testing uses `SimulatedPostgresStore` with Python's in-memory `asyncio.Lock()`.
- **Evaluation:** While this verifies the FastAPI dependency wiring, status codes, and non-insertion logic, it does not execute concurrent transactions against an actual PostgreSQL engine using independent TCP connection pool slots or a synchronized barrier (e.g. `threading.Barrier`).
- **Database Status:** Part 3 of the test suite intentionally skipped execution against Supabase because the migration has not been applied to production (per user instructions).
- **Required Follow-up:** Before general production deployment, execute a live concurrency test against an isolated test/staging PostgreSQL instance using 10 parallel connections with a synchronized trigger.

---

### Check 11: Rollback Object Isolation
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events_rollback.sql#L6-L8`  
**Analysis:**
The rollback file contains:
```sql
DROP FUNCTION IF EXISTS public.cleanup_rate_limit_events(INT, INT);
DROP FUNCTION IF EXISTS public.check_rate_limit(TEXT, INT, INT);
DROP TABLE IF EXISTS public.rate_limit_events;
```
- Drops strictly the two procedures and the one unlogged table created in migration `001`.
- Does not use `CASCADE` on existing schema objects.
- Does not modify or drop `projects`, `generated_assets`, `profiles`, or any Supabase auth tables.

---

### Check 12: Zero-Cost Architecture Verification
**Status:** **PASS**  
**File & Lines:** `database/migrations/20261117_001_rate_limit_events.sql#L19`; `backend/app/core/rate_limiter.py#L63-L111`  
**Analysis:**
- **No Redis Dependency:** Setting `RATE_LIMIT_STORE=postgres` completely bypasses Redis. No Redis cloud instance or Redis container is required.
- **Zero Incremental Cost:** Uses the existing Supabase free PostgreSQL instance.
- **WAL Protection:** `UNLOGGED` table avoids WAL disk writes, conserving Supabase free-tier database IOPS and bandwidth.
- **No Paid Extensions:** Works with standard PostgreSQL core features (`pg_advisory_xact_lock`, PL/pgSQL). Scheduled cleanup can run via Supabase's free `pg_cron` extension or via a backend background worker.

---

## 3. Discrepancies & Errata Found

1. **Documentation Schema Erratum in `docs/PHASE15D_RATE_LIMITER_REPORT.md`:**
   - In Section 2.1 of the report, the markdown code block displays:
     `key VARCHAR(128)` and `created_at TIMESTAMPTZ`.
   - The actual SQL file `database/migrations/20261117_001_rate_limit_events.sql` uses:
     `bucket_key TEXT` and `requested_at TIMESTAMPTZ`.
   - The actual SQL file is correct, robust, and matches the PL/pgSQL function queries (`bucket_key = p_key`). The report's code snippet has a minor naming discrepancy.

2. **Rollback Function Signature in Report:**
   - Section 8.3 of `PHASE15D_RATE_LIMITER_REPORT.md` lists `DROP FUNCTION IF EXISTS public.check_rate_limit(VARCHAR, INT, INT);`.
   - The actual rollback migration `20261117_001_rate_limit_events_rollback.sql` correctly specifies `TEXT, INT, INT`.

---

## 4. Required Fixes Prior to Production Rollout

| Priority | Component | Issue | Action Required |
|:---:|---|---|---|
| **High** | `backend/app/core/rate_limiter.py` | Untrusted `X-Forwarded-For` header spoofing allows cycling supplementary IP rate limits. | Only extract `X-Forwarded-For` if `request.client.host` matches a trusted proxy CIDR/IP list. |
| **Medium** | `backend/test_postgres_rate_limiter.py` | Concurrency test uses `SimulatedPostgresStore` instead of live multi-connection PostgreSQL transactions. | Run multi-connection benchmark on test/staging PostgreSQL instance once provisioned. |
| **Low** | `docs/PHASE15D_RATE_LIMITER_REPORT.md` | Schema code block has column names (`key`, `created_at`) instead of (`bucket_key`, `requested_at`). | Update code snippets in documentation to match the migration file. |

---

## 5. Final Recommendation

### **SAFE TO APPLY TO A TEST DATABASE**

**Rationale:**
1. The migration file `20261117_001_rate_limit_events.sql` is strictly sandboxed, non-destructive, and creates an `UNLOGGED` table with permissions locked to `service_role`.
2. It does not alter, lock, or migrate any existing tables or schemas (`projects`, `profiles`, `generated_assets`).
3. The advisory lock implementation (`pg_advisory_xact_lock`) is safe, automatically released on transaction end, and bounded.
4. The rollback script cleanly removes all newly created objects without cascading to unrelated data.
5. It is safe to execute on a test/staging Supabase database to conduct live multi-connection concurrency benchmarks.
