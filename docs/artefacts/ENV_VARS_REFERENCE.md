# ENV_VARS_REFERENCE.md

## Purpose
Single source of truth for environment variables used in GrantPilot (Plan A).
Prevents configuration drift across Railway services and avoids recurring deployment bugs.

Non-negotiables:
- Backend (Railway) owns auth, quota, Stripe, persistence, and AI execution.
- Frontend (Railway) is a thin client and must not store secrets.
- Cloudflare provides DNS/TLS and static asset caching only; it must not cache authenticated routes.
- Stripe secrets/webhooks are backend-only.
- Plan B (`ngoinfo-copilot`) remains untouched.

## Environments
- PLAN_A_PROD:
  - Backend service: Railway `ngoinfo-grantpilot` (FastAPI)
  - Frontend service: Railway `grantpilot-web` (Next.js)
  - Public domain: https://grantpilot.ngoinfo.org (proxied via Cloudflare)
  - Backend public URL: https://ngoinfo-grantpilot-production.up.railway.app


## Naming Rules
- ALL_CAPS with underscores.
- Do not introduce new env var names without updating this file in the same PR.

---

## BACKEND (Railway) — Required Variables

### A) Core Runtime
| Variable | Required | Example | Notes |
|---|---:|---|---|
| APP_ENV | Yes | prod | dev/staging/prod |
| APP_NAME | Yes | grantpilot | Used in logs/headers |
| APP_BASE_URL | Yes | https://ngoinfo-grantpilot-production.up.railway.app | Must be public URL |
| CORS_ALLOWED_ORIGINS | Yes | https://grantpilot.ngoinfo.org | Comma-separated allowlist |
| LOG_LEVEL | Yes | INFO | DEBUG only in dev |

### B) Database
| Variable | Required | Notes |
|---|---:|---|
| DATABASE_URL | Yes | Injected by Railway Postgres |

### C) Auth (MVP: Google OAuth + Email Magic Link)
No passwords in MVP.

| Variable | Required | Example | Notes |
|---|---:|---|---|
| AUTH_JWT_SIGNING_KEY | Yes | <secret> | Strong secret |
| AUTH_ACCESS_TOKEN_TTL_MIN | Yes | 15 | Access token TTL |
| AUTH_REFRESH_TOKEN_TTL_DAYS | Yes | 30 | Refresh token TTL |
| AUTH_MAGIC_LINK_TTL_MIN | Yes | 15 | Magic link expiry |
| AUTH_ALLOWED_REDIRECT_URLS | Yes | https://grantpilot.ngoinfo.org/auth/callback | Comma-separated allowlist |
| AUTH_RATE_LIMIT_ENABLED | Yes | true | true/false |

### D) Google OAuth
| Variable | Required | Example | Notes |
|---|---:|---|---|
| GOOGLE_OAUTH_CLIENT_ID | Yes | <id> | From Google Cloud Console |
| GOOGLE_OAUTH_CLIENT_SECRET | Yes | <secret> | Backend only |
| GOOGLE_OAUTH_REDIRECT_URI | Yes | https://ngoinfo-grantpilot-production.up.railway.app/auth/google/callback | Must match Google config exactly |
| GOOGLE_OAUTH_SCOPES | Optional | openid,email,profile | Default if omitted |

### E) Email (Resend) — Magic Link Delivery
| Variable | Required | Example | Notes |
|---|---:|---|---|
| EMAIL_PROVIDER | Yes | resend | Locked for MVP |
| EMAIL_FROM_NAME | Yes | GrantPilot | |
| EMAIL_FROM_ADDRESS | Yes | no-reply@ngoinfo.org | Must be verified in Resend |
| EMAIL_API_KEY | Yes | <secret> | Resend API key |

### F) OpenAI
| Variable | Required | Example | Notes |
|---|---:|---|---|
| OPENAI_API_KEY | Yes | <secret> | |
| PROMPT_VERSION | Yes | v1.0.0 | Persist with outputs |

(Models/settings can be added later; MVP requires deterministic policy in prompts.)

### G) Stripe Billing (Test-First)
| Variable | Required | Example | Notes |
|---|---:|---|---|
| STRIPE_MODE | Yes | test | test/live |
| STRIPE_SECRET_KEY | Yes | sk_test_... | Backend only |
| STRIPE_WEBHOOK_SECRET | Yes | whsec_... | Backend only |
| STRIPE_CHECKOUT_SUCCESS_URL | Yes | https://grantpilot.ngoinfo.org/billing/success | Frontend route |
| STRIPE_CHECKOUT_CANCEL_URL | Yes | https://grantpilot.ngoinfo.org/billing/cancel | Frontend route |
| STRIPE_PRICE_ID_GROWTH | Yes | price_... | Monthly for MVP |
| STRIPE_PRICE_ID_IMPACT | Yes | price_... | Monthly for MVP |

Future (post-MVP):
- STRIPE_PRICE_ID_GROWTH_ANNUAL
- STRIPE_PRICE_ID_IMPACT_ANNUAL

### H) Observability (Recommended)
| Variable | Required | Notes |
|---|---:|---|
| SENTRY_DSN | Optional | Strongly recommended |
| SENTRY_ENVIRONMENT | Optional | prod |

### I) Test Mode (Pre-launch only)
| Variable | Required | Notes |
|---|---:|---|
| TEST_MODE | Optional | true/false; when true, enables test-mode token mint endpoint |
| TEST_MODE_SECRET | Conditional | Required when TEST_MODE=true; long random secret |

---

## FRONTEND (Railway) — Allowed Variables Only

Allowed:
| Variable | Required | Example |
|---|---:|---|
| NEXT_PUBLIC_API_BASE_URL | Yes | https://ngoinfo-grantpilot-production.up.railway.app |

Forbidden on frontend (Railway):
- DATABASE_URL
- OPENAI_API_KEY
- STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET
- GOOGLE_OAUTH_CLIENT_SECRET
- AUTH_JWT_SIGNING_KEY
- Any private signing/encryption secrets

---

## Change Control
- Any env var additions/renames require updating this file in the same PR.
- Never use internal Railway URLs (e.g., *.railway.internal) in OAuth, Stripe, or email links.
