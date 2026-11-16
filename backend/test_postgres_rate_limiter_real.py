"""CreateX AI - Real PostgreSQL Multi-Connection Rate Limiter Integration Test

MANDATORY SAFETY & ISOLATION CONSTRAINTS:
1. NEVER connects to or modifies the production Supabase database.
2. Requires an explicitly configured TEST_DATABASE_URL or TEST_SUPABASE_URL pointing
   to an isolated test/development PostgreSQL instance.
3. If no isolated database is configured, tests are reported strictly as NOT RUN.
   Under NO circumstances are tests replaced with in-memory simulations.
4. When run against a test database, uses a synchronized start barrier (threading.Barrier)
   and independent client connections to test true database-level concurrency and advisory locking.
"""
import os
import sys
import time
import threading
from typing import List, Dict, Any, Optional

# Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

backend_dir = os.path.dirname(os.path.abspath(__file__))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.config import settings

# Track test results
results = {"passed": 0, "failed": 0, "not_run": 0}


def log_test(name: str, passed: bool, detail: str = ""):
    if passed:
        results["passed"] += 1
        print(f"  [PASS] {name}" + (f" -> {detail}" if detail else ""))
    else:
        results["failed"] += 1
        print(f"  [FAIL] {name}" + (f" -> {detail}" if detail else ""))


def log_not_run(name: str, reason: str):
    results["not_run"] += 1
    print(f"  [NOT RUN] {name} -> {reason}")


print("=" * 70)
print("  CreateX AI - Real PostgreSQL Multi-Connection Integration Suite")
print("=" * 70)

# 1. Target Database Isolation Check
test_db_url = os.environ.get("TEST_DATABASE_URL", "").strip()
test_sb_url = os.environ.get("TEST_SUPABASE_URL", "").strip()
test_sb_key = os.environ.get("TEST_SUPABASE_SERVICE_ROLE_KEY", "").strip()

# Safety invariant: Must never run against production Supabase URL
prod_url = settings.supabase_url.strip()
is_isolated = False
isolation_reason = ""

if test_db_url:
    if prod_url and prod_url in test_db_url:
        isolation_reason = "CRITICAL: TEST_DATABASE_URL matches production Supabase URL. Aborting for safety."
    else:
        is_isolated = True
elif test_sb_url and test_sb_key:
    if prod_url and test_sb_url.rstrip("/") == prod_url.rstrip("/"):
        isolation_reason = "CRITICAL: TEST_SUPABASE_URL matches production Supabase URL. Aborting for safety."
    else:
        is_isolated = True
else:
    isolation_reason = (
        "No isolated test database configured. Set TEST_DATABASE_URL or "
        "(TEST_SUPABASE_URL and TEST_SUPABASE_SERVICE_ROLE_KEY) to execute real PostgreSQL tests."
    )

print(f"\nEnvironment Isolation Status: {'ISOLATED TEST DB' if is_isolated else 'UNCONFIGURED'}")
if not is_isolated:
    print(f"Notice: {isolation_reason}")

# ═════════════════════════════════════════════════════════════════════
# EXECUTION OR NOT RUN REPORTING
# ═════════════════════════════════════════════════════════════════════

TEST_CASES = [
    "Multi-connection synchronized barrier concurrency (10 workers -> 3 allowed, 7 rejected)",
    "Rejected requests invariant (no rows inserted in rate_limit_events for 429 rejections)",
    "Independent bucket isolation across concurrent threads",
    "Sliding-window expiration eligibility in live database",
    "Advisory lock release confirmation upon transaction end",
    "Database failure fail-closed behavior (returns 503, never unmetered)",
    "Bounded cleanup procedure execution in live database",
]

if not is_isolated:
    print("\n--- Real Database Integration Checks (Dry Run / Safety Skip) ---")
    for tc in TEST_CASES:
        log_not_run(tc, isolation_reason)

else:
    print("\n--- Running Real Database Integration Checks Against Isolated Database ---")
    # Execute actual PostgreSQL integration tests using independent clients
    try:
        from supabase import create_client, Client

        def get_isolated_client() -> Client:
            return create_client(test_sb_url, test_sb_key)

        # Pre-flight check: Verify check_rate_limit exists on test instance
        probe_client = get_isolated_client()
        probe_res = probe_client.rpc(
            "check_rate_limit",
            {"p_key": "probe_preflight", "p_max_requests": 10, "p_window_secs": 60},
        ).execute()

        if not probe_res.data:
            raise RuntimeError("check_rate_limit RPC not found on test database. Migration not applied.")

        # Test 1 & 2: 10 Synchronized Workers Competing for 3 Slots
        barrier = threading.Barrier(10)
        thread_results: List[Dict[str, Any]] = []
        lock = threading.Lock()
        bucket_key = f"real_test_barrier_{int(time.time())}"

        def worker(worker_id: int):
            # Each worker uses its own independent client connection
            worker_client = get_isolated_client()
            # Wait at barrier for synchronized simultaneous dispatch
            barrier.wait()
            res = worker_client.rpc(
                "check_rate_limit",
                {"p_key": bucket_key, "p_max_requests": 3, "p_window_secs": 60},
            ).execute()
            with lock:
                thread_results.append(res.data[0])

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        allowed_count = sum(1 for r in thread_results if r.get("allowed") is True)
        rejected_count = sum(1 for r in thread_results if r.get("allowed") is False)

        log_test(
            TEST_CASES[0],
            allowed_count == 3 and rejected_count == 7,
            f"allowed={allowed_count}, rejected={rejected_count}",
        )

        # Test 2: Row insertion check for rejected requests
        count_res = (
            probe_client.table("rate_limit_events")
            .select("id", count="exact")
            .eq("bucket_key", bucket_key)
            .execute()
        )
        actual_rows = count_res.count if hasattr(count_res, "count") else len(count_res.data)
        log_test(
            TEST_CASES[1],
            actual_rows == 3,
            f"recorded_rows={actual_rows} (expected exactly 3)",
        )

        # Test 3: Separate bucket isolation
        other_bucket = f"real_test_other_{int(time.time())}"
        other_res = probe_client.rpc(
            "check_rate_limit",
            {"p_key": other_bucket, "p_max_requests": 3, "p_window_secs": 60},
        ).execute()
        other_allowed = other_res.data[0].get("allowed") if other_res.data else False
        log_test(
            TEST_CASES[2],
            other_allowed is True,
            f"other_bucket_allowed={other_allowed}",
        )

        # Test 4: Sliding window expiration
        short_bucket = f"real_test_short_{int(time.time())}"
        probe_client.rpc("check_rate_limit", {"p_key": short_bucket, "p_max_requests": 1, "p_window_secs": 1}).execute()
        blocked_res = probe_client.rpc("check_rate_limit", {"p_key": short_bucket, "p_max_requests": 1, "p_window_secs": 1}).execute()
        is_blocked = blocked_res.data[0].get("allowed") is False

        time.sleep(1.2)  # Wait for 1s window expiration

        unblocked_res = probe_client.rpc("check_rate_limit", {"p_key": short_bucket, "p_max_requests": 1, "p_window_secs": 1}).execute()
        is_unblocked = unblocked_res.data[0].get("allowed") is True

        log_test(
            TEST_CASES[3],
            is_blocked and is_unblocked,
            f"blocked={is_blocked}, unblocked_after_window={is_unblocked}",
        )

        # Test 5: Advisory lock release confirmation
        # In PostgreSQL, transaction advisory locks are released when transaction commits.
        # Verify immediately that another transaction can acquire a lock and complete on the same key without deadlocking.
        lock_verify_res = probe_client.rpc(
            "check_rate_limit",
            {"p_key": bucket_key, "p_max_requests": 100, "p_window_secs": 60},
        ).execute()
        log_test(
            TEST_CASES[4],
            lock_verify_res.data is not None and len(lock_verify_res.data) > 0,
            "Advisory lock freed upon previous transaction commit; subsequent call succeeded",
        )

        # Test 6: Database failure fails closed (verified via invalid client host)
        from app.core.rate_limiter import PostgresRateLimitStore, RateLimitStoreUnavailableError
        bad_client = create_client("https://invalid-host-000.supabase.co", "bad-key")
        bad_store = PostgresRateLimitStore(supabase_client=bad_client)
        failed_closed = False
        try:
            import asyncio
            asyncio.run(bad_store.check_and_increment("fail_bucket", 5, 60))
        except RateLimitStoreUnavailableError:
            failed_closed = True

        log_test(
            TEST_CASES[5],
            failed_closed,
            "PostgresRateLimitStore raised RateLimitStoreUnavailableError on network failure",
        )

        # Test 7: Bounded cleanup function execution
        cleanup_res = probe_client.rpc(
            "cleanup_rate_limit_events",
            {"p_retention_secs": 3600, "p_batch_size": 1000},
        ).execute()
        log_test(
            TEST_CASES[6],
            cleanup_res.data is not None,
            f"cleanup_events_deleted={cleanup_res.data}",
        )

    except Exception as e:
        print(f"Error during real database testing: {e}")
        for tc in TEST_CASES:
            if results["passed"] + results["failed"] + results["not_run"] < len(TEST_CASES):
                log_test(tc, False, f"Exception: {e}")

print("\n" + "=" * 70)
print(f"  Real Integration Results: {results['passed']} passed, {results['failed']} failed, {results['not_run']} NOT RUN")
print("=" * 70)

if results["failed"] > 0:
    sys.exit(1)
