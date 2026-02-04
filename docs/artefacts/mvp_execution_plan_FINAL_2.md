# GrantPilot MVP Execution Plan (FINAL)

Status: **Canonical — LOCKED FOR BUILD**  
Version: **3.1 (FINAL - Post Audit)**  
Last updated: **2026-02-04**  
Timeline: **7 Days**  
Audit Reference: **BACKEND_AUDIT_20260204.md**

## Authoritative Inputs
- BACKEND_AUDIT_20260204.md (Claude Code audit, definitive)
- AS_IS_AUDIT_20260202.md (Cursor audit, repo-based)
- API_CONTRACT.md, MVP_SCOPE_LOCK.md, PRICING_AND_ENTITLEMENTS.md
- DB_FIELD_CONTRACT_*.md (all field contracts)
- OPENAI_PROMPTS_LIBRARY.md, PROMPT_INPUTS_FIELD_MAPPING.md

---

## 0. Purpose & Rules (Non-Negotiable)

This file is the **single source of truth** for all work until public go-live.

### Execution Rules
1. Each **C-XX** corresponds to **exactly one Cursor prompt**, **one GitHub commit**, and **one Railway deploy**
2. Work **must follow the order listed** — no skipping, no reordering
3. Cursor must **STOP and report** if a section cannot be completed without violating contracts
4. Dependencies must be satisfied before starting a commit
5. Exit criteria must ALL pass before marking complete

### How to Use in New Chats
```
"We are working on GrantPilot. Use `mvp_execution_plan_FINAL.md` as the 
authoritative execution plan. We are currently at **C-XX**. Do not analyse 
prior chats. Read the file and continue from current state."
```

---

## 1. Current State Summary (From BACKEND_AUDIT_20260204)

### ✅ What Works
| Component | Status | Notes |
|-----------|--------|-------|
| Auth: Google OAuth | ✅ Working | `auth.py:141-175` |
| Auth: Magic link | ✅ Working | `auth.py:285-398` |
| Auth: Refresh/logout | ✅ Working | `auth.py:398-445` |
| Auth: Test-mode mint | ✅ Working | Properly gated |
| Health endpoint | ✅ Working | `health.py:9` |

### 🔴 P0 Critical Blockers (6 Issues - Must Fix First)

| ID | Issue | Impact | Root Cause |
|----|-------|--------|------------|
| **A1** | `user_plans` column mismatch | **RUNTIME CRASH** - Every UserPlan query fails | Model uses `current_period_start/end`, migration has `billing_period_start/end` |
| **A2** | `ngo_profiles` attribute mismatch | **RUNTIME CRASH** - All profile operations fail | Model: `organization_country_of_registration`, DB: `country_of_registration` |
| **A3** | `UsageLedger` phantom columns | **SILENT DATA LOSS** | Service writes `period_start/period_end` which don't exist |
| **A4** | Entitlements infinite recursion | **RUNTIME CRASH** | Route function `get_entitlements` shadows imported function |
| **A5** | CORS middleware missing | **FRONTEND BLOCKED** | Config validates origins but never applies middleware |
| **A6** | OpenAI errors unhandled | **UNSTRUCTURED 500s** | `RuntimeError` not caught by domain error handler |

### 🟡 Additional Issues Found

| Issue | Severity | Location |
|-------|----------|----------|
| NGO profile routes missing `/api` prefix | P2 | `ngo_profile.py` mounted at `/ngo-profile` not `/api/ngo-profile` |
| Auth hardcodes `plan="FREE"` in tokens | P1 | `auth.py:258,377,430,492` |
| Hardcoded redirect URL | P2 | `auth.py:26-27` should use config |
| Rate limiting is in-memory only | P2 | Won't work across multiple workers |

### ❌ Missing Features (Zero Implementation)

| Feature | Evidence | Dependency Gap |
|---------|----------|----------------|
| Proposals | No table, model, migration, route, service | — |
| Proposal regeneration | No endpoint or logic | — |
| DOCX export | No route, service | `python-docx` missing |
| Stripe billing | Config exists, no SDK or handlers | `stripe` missing |
| Transactional emails | Only magic link implemented | — |

### 📊 Endpoint Status

| Endpoint | Status |
|----------|--------|
| `/health` | ✅ Working |
| `/api/auth/*` (all 7) | ✅ Working |
| `/api/me/entitlements` | 🔴 BROKEN (A4: recursion) |
| `/api/fit-scans` (POST/GET) | 🔴 BROKEN (blocked by A1/A2) |
| `/ngo-profile` (all 4) | 🔴 BROKEN (A2: column mismatch) |
| `/api/proposals/*` | ❌ NOT IMPLEMENTED |

---

## 2. Global Execution Invariants

After every C-XX completion, these must hold true:

| Invariant | Verification |
|-----------|--------------|
| No 500s for expected states | Manual test + smoke script |
| No quota consumption on failed/degraded runs | Check usage_ledger |
| API_CONTRACT-compliant error responses | Swagger validation |
| CORS allows only configured origins | Browser preflight test |
| No test endpoints in prod | Check `APP_ENV` gating |

**Violation requires rollback before proceeding.**

---

## 3. Commit-Driven Execution Plan

---

### DAY 1: Fix Critical Blockers (Nothing Else Works Until These Are Fixed)

---

#### C-00: Database & Model Schema Alignment
**Status:** ⬜ Not Started  
**Priority:** P0 — ALL other commits blocked  
**Estimated Time:** 3-4 hours  
**Dependencies:** None  
**Audit Refs:** A1, A2, A3, C1, C2, C3, C4

**Scope:**

**Part 1: Create migration `0007_schema_alignment.py`**

```python
# Add to users table
op.add_column('users', sa.Column('stripe_customer_id', sa.Text(), nullable=True))
op.create_unique_constraint('uq_users_stripe_customer_id', 'users', ['stripe_customer_id'])

# Fix user_plans - add missing column
op.add_column('user_plans', sa.Column('plan_activated_at', sa.TIMESTAMP(timezone=True), nullable=True))

# Note: billing_period_start/end columns EXIST in DB
# We will fix the MODEL to match, not the migration
```

**Part 2: Fix `app/models/user_plan.py`** (align to migration)

```python
# CHANGE FROM:
current_period_start: Mapped[datetime] = mapped_column(...)
current_period_end: Mapped[datetime] = mapped_column(...)

# CHANGE TO:
billing_period_start: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
billing_period_end: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
plan_activated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
stripe_subscription_id: Mapped[str] = mapped_column(Text, nullable=True)
```

**Part 3: Fix `app/models/ngo_profile.py`** (A2)

```python
# CHANGE FROM (line 24):
organization_country_of_registration: Mapped[str] = mapped_column(Text, nullable=False)

# CHANGE TO:
country_of_registration: Mapped[str] = mapped_column(Text, nullable=False)
```

**Part 4: Fix `app/models/user.py`** (add stripe_customer_id)

```python
# ADD:
stripe_customer_id: Mapped[str] = mapped_column(Text, nullable=True, unique=True)
```

**Part 5: Fix `app/services/quota_service.py`** (A3)

```python
# CHANGE FROM (lines 167-168):
period_start=plan.current_period_start if plan.plan_name != PLAN_FREE else None,
period_end=plan.current_period_end if plan.plan_name != PLAN_FREE else None,

# CHANGE TO (use correct column names):
# Option A: Remove these lines entirely (columns don't exist in UsageLedger)
# Option B: Add columns to UsageLedger migration and model first

# RECOMMENDED: Option A - remove phantom column writes
# Just delete the period_start and period_end lines from UsageLedger creation
```

**Part 6: Update quota_service.py period references**

```python
# CHANGE all references from:
plan.current_period_start → plan.billing_period_start
plan.current_period_end → plan.billing_period_end
```

**Exit Criteria:**
- [ ] Migration `0007` runs without error
- [ ] `alembic upgrade head` succeeds on Railway
- [ ] `UserPlan` queries work without column errors
- [ ] `NGOProfile` CRUD operations work
- [ ] `UsageLedger` creation works without phantom column errors
- [ ] `User` model includes `stripe_customer_id`

**Verification:**
```bash
alembic upgrade head
python -c "from app.models import User, UserPlan, NGOProfile, UsageLedger; print('All models OK')"
```

---

#### C-00B: Fix Entitlements Recursion Bug
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 15 minutes  
**Dependencies:** None (can parallel with C-00)  
**Audit Ref:** A4

**Scope:**

Fix `app/api/routes/entitlements.py`:

```python
# CHANGE FROM:
from app.services.quota_service import get_entitlements

@router.get("/me/entitlements", ...)
def get_entitlements(db, current_user):  # ← shadows import!
    return get_entitlements(db, current_user.id)  # ← infinite recursion

# CHANGE TO:
from app.services.quota_service import get_entitlements as fetch_entitlements

@router.get("/me/entitlements", ...)
def get_user_entitlements(db, current_user):  # ← unique name
    return fetch_entitlements(db, current_user.id)  # ← calls service
```

**Exit Criteria:**
- [ ] `GET /api/me/entitlements` returns valid JSON (not RecursionError)

**Verification:**
```bash
curl -X GET $BASE_URL/api/me/entitlements -H "Authorization: Bearer $TOKEN"
# Should return entitlements JSON, not 500
```

---

#### C-01A: CORS Middleware
**Status:** ⬜ Not Started  
**Priority:** P0 — Frontend blocked without this  
**Estimated Time:** 30 minutes  
**Dependencies:** None (can parallel)  
**Audit Ref:** A5, F1

**Scope:**

Add to `app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

# After app = FastAPI(...)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Exit Criteria:**
- [ ] Frontend can call API without CORS errors
- [ ] OPTIONS preflight returns correct headers

**Verification:**
```bash
curl -X OPTIONS $BASE_URL/api/me/entitlements \
  -H "Origin: https://grantpilot.ngoinfo.org" \
  -H "Access-Control-Request-Method: GET" -v
# Should see Access-Control-Allow-Origin header
```

---

### DAY 2: Stabilize Existing Features

---

#### C-01: Auth Hardening
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-00, C-00B, C-01A  
**Audit Refs:** F4, F5

**Scope:**

**Part 1: Fix hardcoded redirect URL** (`auth.py:26-27`)

```python
# CHANGE FROM:
AUTH_POST_LOGIN_REDIRECT_URL = "https://grantpilot.ngoinfo.org/auth/callback"

# CHANGE TO:
# Use settings.AUTH_POST_LOGIN_REDIRECT_URL from config
```

**Part 2: Fix plan="FREE" hardcoding** (`auth.py:258,377,430,492`)

```python
# CHANGE FROM:
access_token = create_access_token(user_id=user.id, email=user.email, plan="FREE")

# CHANGE TO:
# Fetch actual plan from user_plans table
user_plan = db.query(UserPlan).filter(UserPlan.user_id == user.id).first()
plan_name = user_plan.plan_name if user_plan else "FREE"
access_token = create_access_token(user_id=user.id, email=user.email, plan=plan_name)
```

**Part 3: Magic link email format**
- Ensure email contains clickable link, not raw token
- Link format: `{FRONTEND_URL}/auth/magic-link?token={token}`

**Part 4: Verify test-mode gating**
- Confirm `POST /api/auth/test-mode/mint` returns 404 when `TEST_MODE=false`

**Exit Criteria:**
- [ ] Redirect URL comes from config
- [ ] Access tokens contain actual user plan
- [ ] Magic link email has clickable link
- [ ] Test-mode properly gated

---

#### C-02: AI Degradation & Error Handling
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-00  
**Audit Ref:** A6

**Scope:**

**Part 1: Wrap OpenAI errors in DomainError**

Update `app/integrations/openai_client.py`:

```python
# CHANGE FROM (line 45):
raise RuntimeError(f"OpenAI request failed: {resp.status_code} {resp.text}")

# CHANGE TO:
from app.core.errors import DomainError
raise DomainError(
    error_code="AI_SERVICE_ERROR",
    message="AI service temporarily unavailable",
    details={"status_code": resp.status_code}
)
```

**Part 2: Add catch-all for unexpected errors in `main.py`**

```python
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    # Log the actual error
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
            "request_id": getattr(request.state, "request_id", None)
        }
    )
```

**Part 3: Implement DEGRADED_* handling in fit scan**

Update `app/services/fit_scan_service.py` to:
- Catch AI errors
- Return degraded response (not 500)
- Do NOT consume quota on degraded path

**Exit Criteria:**
- [ ] OpenAI failures return structured error (not raw 500)
- [ ] All errors match API_CONTRACT schema
- [ ] Fit scan degradation doesn't consume quota

---

#### C-03: Quota Enforcement Verification
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 2 hours  
**Dependencies:** C-00 (schema fix required)

**Scope:**
1. Verify quota check uses correct column names (`billing_period_start/end`)
2. Verify atomic check + decrement
3. Verify 429 response on exhaustion
4. Verify plan-specific messaging

**Exit Criteria:**
- [ ] Quota exhaustion returns 429 (not 403)
- [ ] Free plan lifetime limits work
- [ ] Growth/Impact monthly limits work
- [ ] No double consumption on retries

---

### DAY 3: Fit Scan Certification

---

#### C-04: Fit Scan End-to-End Certification
**Status:** ⛔ Blocked by C-00, C-00B, C-02, C-03  
**Priority:** P1  
**Estimated Time:** 2-3 hours  
**Dependencies:** C-00, C-00B, C-02, C-03

**Scope:**

Test matrix (all must pass):

| Scenario | Expected |
|----------|----------|
| Valid opportunity + complete profile | Fit scan created, quota decremented |
| Missing requirements_json | Degraded response, no quota consumed |
| Incomplete profile | 409 PROFILE_INCOMPLETE with missing_fields |
| Quota exhausted | 429 QUOTA_EXCEEDED |
| AI timeout/error | Degraded response, no quota consumed |

**Exit Criteria:**
- [ ] All test matrix scenarios pass
- [ ] Persisted fields match DB_FIELD_CONTRACT_FIT_SCANS
- [ ] Fit Scan marked "production certified"

---

### DAY 4: Proposal Foundation

---

#### C-05A: Proposal Database Foundation
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 3 hours  
**Dependencies:** C-00

**Scope:**

**Part 1: Create `docs/artefacts/DB_FIELD_CONTRACT_PROPOSALS.md`**

**Part 2: Create migration `0008_proposals.py`**

```python
# proposals table
op.create_table(
    'proposals',
    sa.Column('id', sa.UUID(), primary_key=True, server_default=sa.text('gen_random_uuid()')),
    sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    sa.Column('funding_opportunity_id', sa.UUID(), sa.ForeignKey('funding_opportunities.id'), nullable=False),
    sa.Column('fit_scan_id', sa.UUID(), sa.ForeignKey('fit_scans.id'), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    sa.Column('status', sa.Text(), nullable=False, server_default='DRAFT'),
    sa.Column('plan_at_creation', sa.Text(), nullable=False),
    sa.Column('prompt_version', sa.Text(), nullable=False),
    sa.Column('content_json', sa.dialects.postgresql.JSONB(), nullable=False),
    sa.Column('regeneration_count', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
)
op.create_index('ix_proposals_user_created', 'proposals', ['user_id', 'created_at'])
op.create_index('ix_proposals_opportunity', 'proposals', ['funding_opportunity_id'])
```

**Part 3: Create model `app/models/proposal.py`**

**Part 4: Create schemas `app/schemas/proposal.py`**

**Part 5: Register in `app/models/__init__.py`**

**Exit Criteria:**
- [ ] Migration runs successfully
- [ ] Model imports without error
- [ ] DB contract committed

---

#### C-05B: Proposal Creation Endpoint
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 5-6 hours  
**Dependencies:** C-05A, C-02, C-03

**Scope:**

1. Create `app/api/routes/proposals.py`:
   - `POST /api/proposals`
   - `GET /api/proposals/{id}`

2. Create `app/services/proposal_service.py`

3. Create `app/ai/proposal_executor.py`

4. Register router in `app/main.py`

5. Quota enforcement (Free: 1 lifetime, Growth: 3/mo, Impact: 5/mo)

**Exit Criteria:**
- [ ] POST creates proposal from requirements_json
- [ ] GET retrieves proposal
- [ ] Quota enforced correctly
- [ ] Degraded response if requirements incomplete

---

### DAY 5: Proposal Completion & Export

---

#### C-06: Proposal Regeneration
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 3 hours  
**Dependencies:** C-05B

**Scope:**
- `POST /api/proposals/{id}/regenerate`
- Plan gating (Free: forbidden, Growth/Impact: max 3)
- Increment regeneration_count
- Track in usage_ledger

**Exit Criteria:**
- [ ] Free plan gets 403
- [ ] Growth/Impact limited to 3 regenerations
- [ ] Content actually changes

---

#### C-07: DOCX Export
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 4 hours  
**Dependencies:** C-05B

**Scope:**
1. Add `python-docx` to requirements.txt
2. Create `POST /api/proposals/{id}/export`
3. Generate DOCX with proposal content
4. Return signed URL (24hr expiry)

**Exit Criteria:**
- [ ] Export returns valid URL
- [ ] URL downloads valid DOCX
- [ ] Re-download same version: no quota hit

---

### DAY 6: Stripe Billing

---

#### C-08: Stripe Subscription Lifecycle
**Status:** ⬜ Not Started  
**Priority:** P1  
**Estimated Time:** 6-8 hours  
**Dependencies:** C-00 (stripe_customer_id)

**Scope:**
1. Add `stripe` to requirements.txt
2. Create `app/api/routes/stripe.py`:
   - `POST /api/billing/checkout`
   - `POST /api/billing/webhook`
   - `GET /api/billing/portal`
3. Webhook handlers per STRIPE_INTEGRATION_SPEC
4. Signature verification + idempotency

**Exit Criteria:**
- [ ] Checkout creates session
- [ ] Webhook activates/updates plans
- [ ] Signature verification rejects invalid
- [ ] Idempotent event handling

---

### DAY 7: Emails & Production Hardening

---

#### C-09: Transactional Emails
**Status:** ⬜ Not Started  
**Priority:** P2  
**Estimated Time:** 3 hours  
**Dependencies:** C-05B, C-07

**Scope:**
- Email service for: proposal ready, export ready
- Non-prod suppression
- Idempotency

**Exit Criteria:**
- [ ] Emails sent on correct events
- [ ] No duplicates
- [ ] Non-prod suppressed

---

#### C-10: Production Hardening
**Status:** ⬜ Not Started  
**Priority:** P0  
**Estimated Time:** 4 hours  
**Dependencies:** All previous

**Scope:**
1. Schema verification via psql
2. Remove/gate test-mode endpoint
3. Environment variable audit
4. Smoke test suite
5. User journey verification (J1-J6)

**Exit Criteria:**
- [ ] All smoke tests pass
- [ ] All journeys complete
- [ ] Security checklist complete

---

## 4. Definition of Go-Live

### Soft Launch (Day 7)
- C-00 through C-07 COMPLETE
- C-10 smoke tests pass
- Stripe in test mode OR manual plan assignment

### Full Launch
- C-08 (Stripe) live mode
- C-09 (Emails) complete
- C-10 fully verified

---

## 5. Dependency Graph

```
C-00 (Schema) ─┬─→ C-00B (Entitlements fix)
               │
               ├─→ C-01A (CORS) ─→ C-01 (Auth) ─→ C-09 (Emails)
               │
               ├─→ C-02 (AI Degradation) ─┬─→ C-04 (Fit Scan Cert)
               │                          │
               ├─→ C-03 (Quota) ──────────┘
               │
               ├─→ C-05A (Proposal DB) ─→ C-05B (Proposal API) ─→ C-06 (Regen) ─→ C-07 (Export)
               │
               └─→ C-08 (Stripe)

All ──────────────────────────────────────────────────────────────────────→ C-10 (Hardening)
```

---

## 6. Commit Status Tracker

| Commit | Status | Blocks | Est. Hours |
|--------|--------|--------|------------|
| C-00 | ⬜ Not Started | Everything | 3-4h |
| C-00B | ⬜ Not Started | Entitlements | 0.25h |
| C-01A | ⬜ Not Started | Frontend | 0.5h |
| C-01 | ⬜ Not Started | — | 2-3h |
| C-02 | ⬜ Not Started | C-04 | 2-3h |
| C-03 | ⬜ Not Started | C-04 | 2h |
| C-04 | ⛔ Blocked | — | 2-3h |
| C-05A | ⬜ Not Started | C-05B | 3h |
| C-05B | ⬜ Not Started | C-06, C-07 | 5-6h |
| C-06 | ⬜ Not Started | — | 3h |
| C-07 | ⬜ Not Started | — | 4h |
| C-08 | ⬜ Not Started | — | 6-8h |
| C-09 | ⬜ Not Started | — | 3h |
| C-10 | ⬜ Not Started | Launch | 4h |

**Total Estimated: 40-48 hours**

---

## 7. Critical Fixes Summary (For Quick Reference)

| File | Line(s) | Fix |
|------|---------|-----|
| `app/models/user_plan.py` | 31-38 | Rename `current_period_*` → `billing_period_*`, add `stripe_subscription_id` |
| `app/models/ngo_profile.py` | 24 | Rename `organization_country_of_registration` → `country_of_registration` |
| `app/models/user.py` | — | Add `stripe_customer_id` column |
| `app/api/routes/entitlements.py` | 7,13 | Rename function to avoid shadowing import |
| `app/main.py` | — | Add CORS middleware |
| `app/services/quota_service.py` | 167-168 | Remove phantom `period_start/period_end` |
| `app/services/quota_service.py` | various | Change `current_period_*` → `billing_period_*` |
| `app/integrations/openai_client.py` | 45 | Wrap RuntimeError in DomainError |
| `app/api/routes/auth.py` | 258,377,430,492 | Fetch actual plan instead of hardcoding "FREE" |
| `app/api/routes/auth.py` | 26-27 | Use config for redirect URL |
| `requirements.txt` | — | Add `stripe`, `python-docx` |

---

## 8. Change Control

This file may only be modified if:
1. Pranab explicitly approves a change, AND
2. The change is committed before further development

Any deviation without update is considered drift.

---

**END OF DOCUMENT**
