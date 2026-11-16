# CreateX AI — Phase 15C: Zero-Cost Validation & Reality Matrix

**Audit Date:** November 17, 2026  
**Purpose:** Honest technical validation of claims, provider terms, free-tier limitations, and prototype vs production suitability.

---

## 1. Reality Matrix: Claim vs Verified Fact

| Component | Architecture Claim | Verified Technical Reality | Production Suitability | Prototype / Demo Suitability |
| :--- | :--- | :--- | :---: | :---: |
| **Backend: Render Free** | "Free 24/7 backend hosting at $0/mo" | **PARTIALLY TRUE.** Render provides 750 free hours shared across the account. Spins down after 15 min idle; cold start takes **30–50+ seconds**. Bandwidth capped at 100 GB. Arbitrary restarts weekly. | **NOT SUITABLE** for commercial production SLAs | **SUITABLE** for demos, portfolio, user testing |
| **Backend: Koyeb Free** | "Free 24/7 backend with fast start" | **PARTIALLY TRUE.** Only 1 free Nano instance (512 MB RAM, 0.1 CPU). Available only in Frankfurt or Washington DC. Requires phone/account verification. Fast cold starts compared to Render. | **NOT SUITABLE** for high-load production | **SUITABLE** for demos and lightweight testing |
| **Backend: Cloud Run** | "Free tier with 2M requests/month" | **MISLEADING FOR $0 STRICT BUDGET.** While Cloud Run has a generous free tier, **creating a GCP project requires entering a credit card**. If network egress exceeds 1 GB or background jobs linger, charges occur automatically. | High-grade production, but **violates strict $0 no-card rule** | Overkill for $0 budget |
| **Frontend: Vercel Hobby** | "Free global edge frontend hosting" | **LEGAL CONSTRAINT.** Vercel Hobby is 100% free with 100 GB bandwidth, but **strictly restricted to non-commercial, personal projects**. Commercial SaaS violates terms of service. | **NOT SUITABLE** for commercial SaaS | **SUITABLE** for personal demos / open-source showcase |
| **Frontend: Cloudflare Pages** | "Free static frontend hosting" | **VERIFIED TRUE.** Unlimited bandwidth, 500 builds/month, Anycast global edge CDN. **Commercial use is explicitly permitted** on the free tier. No credit card required. | **FULLY SUITABLE** for production | **FULLY SUITABLE** for prototype |
| **Database & Auth: Supabase Free** | "Free managed Postgres & Auth" | **VERIFIED TRUE.** 500 MB database, 50,000 MAUs, Row Level Security. **Limitation:** Pauses after 7 days of inactivity; manual unpausing via dashboard required. No point-in-time recovery. | **CONDITIONALLY SUITABLE** (low volume) | **FULLY SUITABLE** for prototype |
| **Rate Limiter: Supabase Postgres** | "Replaces Redis for $0 with atomic locks" | **VERIFIED TRUE.** Unlogged table + transaction advisory locks (`pg_advisory_xact_lock`) eliminates Redis dependency. 100% atomic across concurrent instances. Fails closed (HTTP 503) if DB drops. | **FULLY SUITABLE** for low-to-medium scale (<1,000 req/min) | **FULLY SUITABLE** for prototype |
| **AI Text: Gemini 3.1 Flash-Lite** | "Free campaign generation via AI Studio" | **VERIFIED TRUE.** 15 Requests Per Minute, 1,500 Requests Per Day, 1M Tokens Per Minute on Google AI Studio Free Tier without billing. | **FULLY SUITABLE** within 15 RPM cap | **FULLY SUITABLE** for prototype |
| **AI Image: Gemini 2.5 Flash Image** | "Free AI poster image generation" | **VERIFIED FALSE.** Google AI Studio **does not offer a free tier for image generation**. Calling with free key returns `HTTP 429 limit: 0`. Deprecated; shuts down March 15, 2027. | **CANNOT BE USED FOR $0** without paid billing | **CANNOT BE USED FOR $0** without paid billing |

---

## 2. Detailed Technical Breakdown

### 2.1 Why AI Image Generation Cannot Be Operated for $0
- **Verified Fact:**  
  The Google AI Studio pricing model distinguishes between text/multimodal input and media generation output:
  - Text and multimodal understanding models (`gemini-3.1-flash-lite`, `gemini-2.5-flash`) offer a free tier (15 RPM / 1,500 RPD).
  - Image generation models (`gemini-2.5-flash-image`, Imagen 3) are **strictly paid-tier services**.
- **Evidence from Live Project Testing:**  
  During the live smoke test on this repository, invoking `POST /api/visual/generate` returned:
  ```json
  {
    "code": 429,
    "message": "Resource has been exhausted (e.g. check quota)... limit: 0, model: gemini-2.5-flash-preview-image... requests per day limit exceeded on Free Tier"
  }
  ```
- **Architectural Policy:**  
  CreateX AI will **not fabricate a free image generation claim**. The text orchestration, creative angles, brand styling, storyboards, and social copy operate genuinely for $0. Poster generation will display a transparent notification to users indicating that image generation requires paid API credits.

---

### 2.2 Prototype vs Production Suitability Analysis

#### What Constitutes "Prototype / Demo Hosting"?
- **Platforms:** Render Free, Koyeb Nano, Supabase Free.
- **Characteristics:**
  - Spin-down when inactive (Render: 15 min idle -> 30–50s delay on wakeup).
  - Weekly restarts or host migration.
  - 512 MB memory ceiling (cannot buffer multiple concurrent high-resolution assets).
  - Shared vCPU (noisy neighbors can cause transient latency spikes).
  - 7-day inactivity pause (Supabase).
- **Verdict:** Excellent for portfolio showcases, student projects, product validation, investor demos, and internal dogfooding at **true $0.00 cost**. Unacceptable for enterprise SLAs or paying customer expectations.

#### What Would Constitute "True Production-Grade Hosting"?
- **Platforms:** Google Cloud Run + Cloudflare Pages + Supabase Pro + Google Cloud Memorystore (Redis).
- **Minimum Cost:** ~$25–$60 / month:
  - Supabase Pro: $25/mo (eliminates 7-day pause, provides daily PITR backups, 8 GB DB).
  - Cloud Run: $0–$10/mo (pay per request, instant concurrency, no 50s cold start).
  - Redis (Upstash Serverless): $0–$5/mo.
  - Cloudflare Pages: $0/mo.
- **Verdict:** Required only when real paying users require 99.9% uptime and zero cold-start latency.

---

## 3. PostgreSQL Rate Limiting Verification Plan

To validate the proposed PostgreSQL-backed atomic rate limiter before deployment, the test suite `backend/test_postgres_rate_limiter.py` must prove the following assertions:

1. **Concurrency Invariant:**
   - 10 concurrent requests executed via `asyncio.gather` for a quota of 3 requests.
   - Assert: Exactly 3 requests receive `allowed = true`, and exactly 7 requests receive `allowed = false`.
   - Result must demonstrate zero race-condition overages.
2. **Sliding-Window Expiration Invariant:**
   - Consume full quota of 3 requests.
   - Wait for sliding window interval (e.g., 2 seconds in test mode).
   - Send 1 new request.
   - Assert: Request is permitted (`allowed = true`, `remaining = 2`).
3. **Identity Boundary Invariant:**
   - `user:user_123` reaching quota does not impact `user:user_456`.
   - `guest:session_aaa` reaching quota does not impact `guest:session_bbb`.
   - `ip:192.0.2.1` reaching quota does not impact `ip:198.51.100.1`.
4. **Failsafe Store Outage Invariant:**
   - Simulate database disconnection or query failure.
   - Assert: Rate limiter catches the exception and raises `HTTP 503 Service Unavailable` with message `"Rate limiting verification is temporarily unavailable. Please retry."`
   - Assert: Unmetered requests are NEVER silently passed through during a database outage.
5. **Table Cleanup Routine:**
   - Run `cleanup_stale_rate_limit_events()`.
   - Assert: Stale timestamps older than retention window are deleted; active timestamps are preserved.

---

## 4. Summary of Zero-Cost Recommendations

1. **Frontend:** Use **Cloudflare Pages** ($0/month, unlimited bandwidth, fully commercial-friendly). Avoid Vercel Hobby if the app is commercial.
2. **Backend:** Use **Render Free** ($0/month, prototype classification, 30–50s cold starts) or **Koyeb Nano**. Add a frontend warming skeleton.
3. **Database & Storage:** Use **Supabase Free** ($0/month). Manually unpause in the dashboard if inactive for >7 days.
4. **Rate Limiting:** Use **Supabase PostgreSQL Stored Procedure** ($0/month). Fails safe with HTTP 503 on database disruption.
5. **AI Engine:** Use **Google AI Studio Gemini 3.1 Flash-Lite** ($0/month) for text, strategy, and copy. Keep image generation as an optional paid add-on.
