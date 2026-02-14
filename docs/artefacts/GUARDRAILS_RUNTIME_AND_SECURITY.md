# GUARDRAILS_RUNTIME_AND_SECURITY.md

**Status:** LOCKED – AUTHORITATIVE  
**Version:** 1.0 (Launch Critical Only)  
**Scope:** Bug prevention for 7-day MVP launch  
**Philosophy:** Prevent showstoppers now. Polish after launch.

---

## 0. Purpose

This document contains **ONLY** the rules that prevent:
1. Runtime crashes (500s in core flows)
2. Data corruption (FK violations, partial state)
3. Security breaches (secret leakage, unauthorized access)
4. Quota bypass (double-spending, free tier abuse)

**Everything else can be refined post-launch.**

---

## 1. The Five Showstopper Rules

### Rule 1: FLUSH BEFORE FK REFERENCE (The Bug That Happened)

**Problem:** Referencing `user.id` before flush causes NULL FK violation.

**Solution:**
```python
# ✅ ALWAYS DO THIS
user = User(email=email)
db.add(user)
db.flush()  # user.id now exists
db.refresh(user)

token = AuthRefreshToken(user_id=user.id)  # Safe
db.add(token)
db.commit()
```

**When to flush:**
- Before using auto-generated `id` in FK
- Before self-referential FK (token rotation: new token must exist before `replaced_by_token_id` set)

---

### Rule 2: WRAP AI ERRORS IN DOMAIN ERRORS

**Problem:** OpenAI exceptions become unstructured 500s.

**Solution:**
```python
# app/integrations/openai_client.py

try:
    response = openai.ChatCompletion.create(...)
    return response.choices[0].message.content
    
except openai.error.APIError as e:
    logger.error(f"OpenAI error: {e}", exc_info=True)
    raise DomainError(
        error_code="AI_SERVICE_ERROR",
        message="AI service temporarily unavailable",
        http_status=503
    )
```

**Apply to:** Fit Scan, Proposal generation, any AI call.

---

### Rule 3: ATOMIC QUOTA CHECK + DECREMENT

**Problem:** Race condition allows double-spending quota.

**Solution:**
```python
# ✅ Check and decrement in SINGLE transaction
with db.begin():
    current_usage = db.query(UsageLedger).filter(...).count()
    
    if current_usage >= plan_limit:
        raise DomainError(error_code="QUOTA_EXCEEDED", http_status=429)
    
    db.add(UsageLedger(user_id=user_id, action_type=action_type, ...))
    # Commit on context exit
```

**Never split check and decrement into separate transactions.**

---

### Rule 4: VERIFY STRIPE WEBHOOKS

**Problem:** Unverified webhooks allow plan manipulation.

**Solution:**
```python
@router.post("/api/billing/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(None, alias="Stripe-Signature")
):
    payload = await request.body()
    
    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=stripe_signature,
            secret=settings.STRIPE_WEBHOOK_SECRET
        )
    except stripe.error.SignatureVerificationError:
        raise DomainError(error_code="WEBHOOK_SIGNATURE_INVALID", http_status=400)
    
    return handle_stripe_event(event)
```

**No signature = no processing.**

---

### Rule 5: NO SECRETS IN LOGS OR RESPONSES

**Forbidden in logs:**
- `Authorization: Bearer ...` headers
- Refresh tokens, magic link tokens
- `OPENAI_API_KEY`, `STRIPE_SECRET_KEY`
- Proposal bodies (log `proposal_id` only)

**Forbidden in API responses:**
- Stack traces (catch-all exception handler required)
- SQL queries
- Environment variables

**Solution:**
```python
# app/main.py - Add catch-all handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "request_id": getattr(request.state, "request_id", None)
        }
    )
```

---

## 2. Required Middleware (Add Once, Forget)

### CORS (Frontend Blocked Without This)
```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
```

### Request ID (For Debugging)
```python
# app/middleware/request_id.py
from starlette.middleware.base import BaseHTTPMiddleware
import uuid

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request.state.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

app.add_middleware(RequestIDMiddleware)
```

---

## 3. Transaction Patterns (Copy-Paste These)

### Pattern A: Simple Create with FK
```python
def create_user_with_token(email: str):
    with db.begin():
        user = User(email=email)
        db.add(user)
        db.flush()  # user.id now exists
        db.refresh(user)
        
        token = AuthRefreshToken(user_id=user.id, ...)
        db.add(token)
        # Auto-commit on exit
    
    return user, token
```

### Pattern B: Token Rotation (Self-Referential FK)
```python
def rotate_refresh_token(old_token: AuthRefreshToken):
    with db.begin():
        # Create new token FIRST
        new_token = AuthRefreshToken(user_id=old_token.user_id, ...)
        db.add(new_token)
        db.flush()  # new_token.id now exists
        db.refresh(new_token)
        
        # Now safe to reference new_token.id
        old_token.revoked_at = datetime.utcnow()
        old_token.replaced_by_token_id = new_token.id
    
    return new_token
```

### Pattern C: Long AI Call (Outside Transaction)
```python
def generate_proposal(user_id: UUID, opportunity_id: UUID):
    # Quick transaction: create record
    with db.begin():
        proposal = Proposal(status="GENERATING", ...)
        db.add(proposal)
        db.flush()
        proposal_id = proposal.id
    
    # AI call OUTSIDE transaction (long-running)
    try:
        content = call_openai(...)
        
        # Quick transaction: update status
        with db.begin():
            proposal = db.query(Proposal).filter_by(id=proposal_id).first()
            proposal.status = "READY"
            proposal.content_json = content
    
    except Exception as e:
        # Mark failed (don't consume quota)
        with db.begin():
            proposal = db.query(Proposal).filter_by(id=proposal_id).first()
            proposal.status = "FAILED"
        raise DomainError(error_code="PROPOSAL_GENERATION_FAILED", http_status=500)
    
    return proposal
```

---

## 4. Security Checklist (5-Minute Audit)

**Before deploying ANY endpoint:**

- [ ] **Authorization:** Does it check `resource.user_id == current_user.id`?
- [ ] **FK Safety:** Are all FK references after `db.flush()`?
- [ ] **AI Errors:** Are OpenAI exceptions caught and wrapped?
- [ ] **Quota:** Is check+decrement atomic?
- [ ] **Secrets:** No tokens/keys in logs?

**If any ❌, fix before deploy.**

---

## 5. Stripe Webhook Checklist

- [ ] Signature verification (reject if invalid)
- [ ] Idempotency (check if `stripe_event_id` already processed)
- [ ] Transaction (plan update + webhook log in single transaction)

**Template:**
```python
def handle_stripe_event(event: stripe.Event):
    # Idempotency check
    if db.query(StripeWebhookLog).filter_by(stripe_event_id=event.id).first():
        return {"status": "already_processed"}
    
    with db.begin():
        # Process event (update user_plans, etc.)
        if event.type == "checkout.session.completed":
            update_user_plan(event.data.object)
        
        # Log as processed
        db.add(StripeWebhookLog(stripe_event_id=event.id, processed_at=datetime.utcnow()))
    
    return {"status": "processed"}
```

---

## 6. Email Safety (Resend)

**Non-Critical:** Email failures should NOT block requests.

```python
def send_email(to: str, subject: str, html: str):
    # Non-prod suppression
    if settings.EMAIL_SUPPRESS_SENDING:
        logger.info(f"[EMAIL SUPPRESSED] To: {to}, Subject: {subject}")
        return
    
    try:
        resend.Emails.send({"from": settings.EMAIL_FROM_ADDRESS, "to": to, ...})
    except Exception as e:
        # Log but don't raise (email is non-critical)
        logger.error(f"Email send failed: {e}")
```

---

## 7. DOCX Export Safety

**Critical:** Export must be direct streaming for MVP (no storage layer).

```python
def export_proposal_to_docx(proposal: Proposal):
    # Generate DOCX bytes in-memory
    doc = Document()
    # ... add content ...

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    # Return bytes directly with correct headers in the API layer
    return buffer.getvalue()
```

Post-MVP: S3 signed URLs are allowed only after explicit artefact update.

---

## 8. Railway Production Env Vars (Minimum Required)

```bash
# Core
APP_ENV=prod
DATABASE_URL=postgresql://...  # Injected by Railway

# Auth
AUTH_JWT_SIGNING_KEY=[64+ char random]
AUTH_ALLOWED_REDIRECT_URLS=https://grantpilot.ngoinfo.org/auth/callback

# CORS
CORS_ALLOWED_ORIGINS=https://grantpilot.ngoinfo.org

# OAuth
GOOGLE_OAUTH_CLIENT_ID=...
GOOGLE_OAUTH_CLIENT_SECRET=...
GOOGLE_OAUTH_REDIRECT_URI=https://ngoinfo-grantpilot-production.up.railway.app/api/auth/google/callback

# OpenAI
OPENAI_API_KEY=sk-proj-...

# Stripe
STRIPE_SECRET_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID_GROWTH=price_...
STRIPE_PRICE_ID_IMPACT=price_...

# Email
EMAIL_API_KEY=re_...
EMAIL_FROM_ADDRESS=support@ngoinfo.org
EMAIL_SUPPRESS_SENDING=false

# Storage
S3_ENDPOINT_URL=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_BUCKET_NAME=grantpilot-exports

# Disable test mode in prod
TEST_MODE=false
```

---

## 9. Pre-Deployment Smoke Test

**Run these before marking "done":**

```bash
# Health check
curl $BASE_URL/health

# Auth flow
curl -X POST $BASE_URL/api/auth/magic-link/request -d '{"email":"test@example.com"}'

# Protected endpoint without auth (should 401)
curl $BASE_URL/api/me/entitlements

# Protected endpoint with auth (should 200)
curl -H "Authorization: Bearer $TOKEN" $BASE_URL/api/me/entitlements
```

---

## 10. Post-Launch Improvements (Defer These)

**Good ideas, not critical:**
- [ ] Redis-based rate limiting (in-memory is fine for single instance)
- [ ] Advanced logging (JSON structured logs)
- [ ] Sentry integration (nice to have)
- [ ] Optimistic locking for proposals (low concurrency in MVP)
- [ ] Connection pooling tuning (Railway handles this)
- [ ] Response compression (Railway/Cloudflare handles this)
- [ ] Detailed audit trails (basic logging is enough)

**Ship first. Optimize later.**

---

## 11. Cursor Prompt Template (Use This Format)

```
Implement [endpoint].

CHECKLIST:
- [ ] FK references after db.flush()
- [ ] AI errors wrapped in DomainError
- [ ] Quota check+decrement atomic
- [ ] Authorization: resource.user_id == current_user.id
- [ ] No secrets in logs

REFERENCES:
- API_CONTRACT.md Section X
- GUARDRAILS_RUNTIME_AND_SECURITY.md Rule Y

[Now implement]
```

---

## 12. The Two Questions (When Stuck)

**Question 1:** "Will this crash in production?"  
→ If yes, fix now. If no, defer.

**Question 2:** "Can users steal quota or access others' data?"  
→ If yes, fix now. If no, defer.

**Everything else: ship and iterate.**

---

## 13. Final Rule

**If you violate Rules 1-5, production WILL break.**

**If you skip middleware (Section 2), users can't access the app.**

**If you skip security checklist (Section 4), users can exploit the system.**

**Everything else is optimization.**

---

**Launch in 7 days. Polish in Week 2.**

**END OF DOCUMENT**
