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
| CORS_ALLOWED_ORIGINS | Yes | https://grantpilot.ngoinfo.org,https://staging.grantpilot.ngoinfo.org | Comma-separated allowlist; include all valid origins
| LOG_LEVEL | Yes | INFO | DEBUG only in dev |

### B) Database
| Variable | Required | Notes |
|---|---:|---|
| DATABASE_URL | Yes | Injected by Railway Postgres |

### C) Auth (MVP: Google OAuth + Email Magic Link)
No passwords in MVP.

| Variable | Required | Example | Notes |
|---|---:|---|---|
AUTH_JWT_SIGNING_KEY | Yes | <secret> | Strong secret (min 64 chars, cryptographically random). Generation: openssl rand -base64 64
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
| EMAIL_FROM_NAME | Yes | NGOInfo | |
| EMAIL_FROM_ADDRESS | Yes | support@ngoinfo.org | Must be verified in Resend |
| EMAIL_API_KEY | Yes | <secret> | Resend API key |
| EMAIL_SUPPRESS_SENDING | Yes | false | true/false; when true, do not call Resend and mark email events as SUPPRESSED |

### F) OpenAI
| Variable | Required | Example | Notes |
|---|---:|---|---|
| OPENAI_API_KEY | Yes | <secret> | |
| PROMPT_VERSION | Yes | v1.0.2 | Persist with outputs |
| OPENAI_MODEL_PRIMARY | Yes | gpt-5.4 | Primary model for all AI calls. Must be a valid OpenAI Chat Completions model string. |
| OPENAI_MODEL_FALLBACK | Yes | gpt-5.4-mini | Fallback model used automatically if primary returns HTTP 400 (deprecated/invalid model). |

Note:
- Model selection is now environment-driven (changed from hardcoded constant in v1.0.2, 2026-03-23).
- See OPENAI_PROMPTS_LIBRARY.md Section 1 for the full model strategy including upgrade procedure.
- When upgrading models: set new model as PRIMARY, move previous model to FALLBACK. No code deploy needed.
- Monitor Railway logs for `openai_primary_model_failed` warnings — this means the fallback activated and PRIMARY needs updating.


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
| STRIPE_PORTAL_RETURN_URL | Recommended | https://grantpilot.ngoinfo.org/dashboard | Portal return route |

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

### J) M&E Module (Stage C)
| Variable | Required | Example | Notes |
|---|---:|---|---|
| ME_MODULE_ENABLED | Yes | false | Default off; when true, mounts `/api/reports*` routes |
| ME_DOCUMENTS_S3_ENDPOINT | Conditional | https://... | Required when `ME_MODULE_ENABLED=true`; Railway Buckets S3-compatible endpoint |
| ME_DOCUMENTS_S3_ACCESS_KEY | Conditional | <key> | Required when `ME_MODULE_ENABLED=true` |
| ME_DOCUMENTS_S3_SECRET | Conditional | <secret> | Required when `ME_MODULE_ENABLED=true` |
| ME_DOCUMENTS_S3_BUCKET | Conditional | grantpilot-me-documents | Required when `ME_MODULE_ENABLED=true` |
| ANTHROPIC_API_KEY | Yes | <secret> | Backend + worker; passed explicitly into each Claude Agent SDK subprocess via `ClaudeAgentOptions.env` (`merge_claude_subprocess_env` in `app/reports/agents/claude_sdk_env.py`). Headless runs must not rely on interactive `claude /login` — Railway worker has no terminal. No expiry — store in secrets manager only; never commit, log, or persist in `agent_trace_json`. |
| ME_CLASSIFIER_MODEL | Optional | haiku | Selects classifier model class; default `haiku` when omitted. |
| ME_RECONCILER_MODEL | Optional | opus | E1 knowledge-bank reconciler model class; default `opus` when omitted. |
| ME_RECONCILER_TIMEOUT_SECONDS | Optional | 180 | Per-attempt wall timeout for reconciler agent (D-035: 2 attempts then degraded). |

**Namespace rule:** M&E document uploads use `ME_DOCUMENTS_S3_*` only. Generic `S3_*` names are **reserved** for a future core exports bucket (see GUARDRAILS_RUNTIME_AND_SECURITY.md) and must not be used by M&E.

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

AUTH_POST_LOGIN_REDIRECT_URL | Yes | https://grantpilot.ngoinfo.org/auth/callback | Frontend route for post-OAuth redirect

## Change Control
- Any env var additions/renames require updating this file in the same PR.
- Never use internal Railway URLs (e.g., *.railway.internal) in OAuth, Stripe, or email links.
