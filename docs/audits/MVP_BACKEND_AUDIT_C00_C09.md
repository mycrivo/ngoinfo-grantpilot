# MVP Backend Audit (C-00 to C-09)

## (A) Coverage Matrix

| Plan Item (C-xx + sub-bullet) | Status | Evidence (paths + identifiers) | Notes |
|---|---|---|---|
| C-00: schema/alignment baseline | CONFLICT | `docs/artefacts/mvp_execution_plan_FINAL_2.md` (`Current State` only, `C-00..C-04 complete` note), `alembic/versions/0007_schema_alignment.py` | v4 plan has no explicit C-00 acceptance criteria/section; strict PASS/FAIL not derivable from canonical plan text. |
| C-01: CORS middleware hardening | PASS | `app/main.py` `app.add_middleware(CORSMiddleware, ...)`; plan current-state row for CORS | Implemented and wired. |
| C-02: pre-auth/platform hardening step | CONFLICT | `docs/artefacts/mvp_execution_plan_FINAL_2.md` (no C-02 section present) | Missing explicit C-02 requirements in plan document prevents strict PASS/FAIL. |
| C-03: quota enforcement | PASS | `app/services/quota_service.py` `enforce_quota()`, `record_usage()`; usage wiring in `app/services/fit_scan_service.py`, `app/services/proposal_service.py` | Quota checks and usage tracking exist across implemented flows. |
| C-04: Fit Scan API + persistence + quota semantics | PASS | `app/api/routes/fit_scans.py` POST/GET; `app/services/fit_scan_service.py` run/get + quota + persistence; plan current-state row | Implemented end-to-end. |
| C-05: Authlib OAuth + code exchange | CONFLICT | Plan C-05 section in `docs/artefacts/mvp_execution_plan_FINAL_2.md`; `docs/artefacts/API_CONTRACT.md` auth exchange; `app/api/routes/auth.py` (`OAuth2Client` flow), `app/services/auth_service.py` DB code store, `alembic/versions/0008_oauth_exchange_codes.py` | Plan specifies in-memory one-time code + 400 invalid code, while API_CONTRACT+code use DB-backed code store + 401. Plan asks `app/core/oauth.py` but file absent. |
| C-06: smoke test update for OAuth | PARTIAL | `scripts/smoke_test.py` current checks; plan C-06 requires OAuth start + exchange invalid checks | OAuth checks required by C-06 are not present in smoke script. |
| C-07A: Proposal DB + model + schemas | PARTIAL | `alembic/versions/0011_proposals.py`, `app/models/proposal.py`, `app/schemas/proposal.py` | Proposal DB/model exist, but plan summary response includes opportunity title/recommendation while schema omits them. |
| C-07B: Proposal create/retrieve + prompt runner | CONFLICT | Plan C-07B section; `app/ai/prompt_runner.py`, `app/ai/prompt_inputs_builder.py`, `app/services/proposal_service.py` create path, `app/api/routes/proposals.py` POST/GET | Plan says missing/invalid requirements should return degraded response; implementation returns 422 `REQUIREMENTS_INVALID`. |
| C-08: Proposal regeneration | PASS | Plan C-08 section; route `app/api/routes/proposals.py` regenerate; service `app/services/proposal_service.py` `regenerate_proposal()` and `_regenerate_sections()` | Ownership, plan gating (FREE denied), max 3, retry FAILED, keep MANUAL_REQUIRED, transactional update + `PROPOSAL_REGEN` usage recorded. |
| C-09: DOCX export direct streaming | PARTIAL | Plan C-09 section; route `app/api/routes/proposals.py` export; service `app/services/export_service.py`; dependency in `requirements.txt`; enum in `docs/artefacts/ENUM_REGISTRY.md` | Export exists and idempotency key includes user/proposal/version. Partial: PRICING says first export consumes proposal quota, but entitlements proposal bucket currently counts only `PROPOSAL_CREATE`. |
| API contract consistency for export method | CONFLICT | `docs/artefacts/API_CONTRACT.md` endpoint list vs detailed section | API_CONTRACT is internally inconsistent (GET vs POST for export). |

## (B) Delta List (prioritized)

| Priority | Item | Status | Exact gap | Next step ID to tackle |
|---|---|---|---|---|
| P0 blocker | C-05 contract conflict (auth code store + error semantics + oauth module requirement) | CONFLICT | Plan requires in-memory auth code + 400 invalid code + `app/core/oauth.py`; API_CONTRACT + code use DB-backed store and 401. | C-05 |
| P0 blocker | C-07B requirements invalid behavior drift | CONFLICT | Plan requires degraded response on missing/invalid requirements; implementation returns 422 `REQUIREMENTS_INVALID`. | C-07B |
| P0 blocker | C-09 export quota semantics not aligned with PRICING | PARTIAL | PRICING says first export of version consumes proposal quota; entitlements proposal usage bucket counts only `PROPOSAL_CREATE`. | C-09 |
| P1 | C-06 smoke test update incomplete | PARTIAL | OAuth start/exchange checks required by C-06 are absent in smoke script. | C-06 |
| P1 | C-07A response schema drift | PARTIAL | Plan summary response includes opportunity title + recommendation; schema omits both. | C-07A |
| P1 | API export method ambiguity | CONFLICT | API_CONTRACT has GET in endpoint list and POST in detailed export section. | C-09 |

## (C) Proceed to frontend

**NO**

