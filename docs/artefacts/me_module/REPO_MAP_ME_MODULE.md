# M&E Module — Repository Map

**Status:** Stage A governance · **Runtime package:** `app/reports/` (created Stage C)
**Canonical reference docs:** `docs/artefacts/me_module/`

---

## Boundary (one sentence)

M&E lives in `app/reports/`, imports core, is mounted once from `app/main.py`, and is never imported back by core.

---

## Directory tree (target — Stage C onward)

```
app/reports/                          # ALL M&E runtime code
  __init__.py
  router.py                           # THE mounting seam (sub-router aggregator)
  api/
    routes/
      reports.py                      # /api/reports/*
      report_templates.py             # /api/report-templates
    dependencies/
      entitlements.py                 # report quota guard
  models/
    donor_report.py
    funder_report_template.py
    uploaded_document.py
    report_job.py
  schemas/
    ...
  services/
    report_service.py                 # mirrors app/services/proposal_service.py
    report_inputs_builder.py          # mirrors app/ai/prompt_inputs_builder.py
    document_storage_service.py       # Railway Buckets (Stage C)
    report_export_service.py          # docxtpl — NOT export_service.py
  extraction/
    docling_adapter.py
  agents/                             # Claude Code builds this
    ...
  worker/
    __main__.py
    run_pipeline.py
    job_runner.py
  templates/
    docx/                             # 10 funder .docx templates

alembic/versions/
  0014_me_module_*.py                 # M&E tables only; FKs inward

Procfile                              # add: worker: python -m app.reports.worker
```

**Not runtime code:** `docs/artefacts/me_module/`, legacy `M_E_Module/` (reference copies).

---

## The one mounting seam (backend)

**File:** [`app/main.py`](../../app/main.py)

**Only allowed core touchpoint** (Stage C — behind feature flag):

```python
if settings.ME_MODULE_ENABLED:
    from app.reports.router import router as reports_router
    app.include_router(reports_router)
```

**Today:** seam not yet wired (Stage C). Core [`app/main.py`](../../app/main.py) includes only:

- `health_router`, `auth_router`, `billing_router`, `entitlements_router`
- `fit_scans_router`, `funding_opportunities_router`, `ngo_profile_router`, `proposals_router`

**Router aggregator:** `app/reports/router.py` will include M&E route modules under `/api`.

---

## The one mounting seam (frontend — separate repo)

- Env: `NEXT_PUBLIC_ME_MODULE_ENABLED` (exact name locked Stage B)
- Routes: `/reports/*` (8 screens per wireframes)
- Nav entry hidden when flag off

This backend repo has **no frontend source**; API contract in `docs/artefacts/API_CONTRACT.md` must be self-sufficient.

---

## What M&E may import from core

| Core module | Use |
|-------------|-----|
| `app.core.config`, `app.core.errors`, `app.core.security` | Settings, domain errors, JWT |
| `app.api.dependencies.auth` | `get_current_user` |
| `app.api.dependencies.quota` | Quota patterns (extend for reports) |
| `app.services.auth_service` | User/plan resolution |
| `app.services.quota_service` | Usage ledger, entitlements |
| `app.services.billing_service` | Impact Pro / IMPACT_PRO (Stage J) |
| `app.services.profile_service` | NGO profile context |
| `app.services.email_service` | Lifecycle emails |
| `app.ai.prompt_runner` | Synthesis / humaniser path |
| `app.ai.prompt_inputs_builder` | Pattern reference |
| `app.integrations.openai_client` | OpenAI HTTP client |
| `app.models.user`, `app.models.proposal`, … | FK targets only |

## What core must NOT import

- **Nothing from `app.reports.*`** except the conditional seam in `app/main.py`.
- Enforced by [`.cursor/hooks/isolation_veto.py`](../../.cursor/hooks/isolation_veto.py).

## Forbidden core modifications

Do **not** modify:

- [`app/services/export_service.py`](../../app/services/export_service.py)
- [`app/services/proposal_service.py`](../../app/services/proposal_service.py)
- [`app/api/routes/proposals.py`](../../app/api/routes/proposals.py)
- Core models/migrations for M&E purposes

See [`.cursor/rules/40-scope-fence.mdc`](../../.cursor/rules/40-scope-fence.mdc).

---

## Data (4 tables — Stage B contracts, Stage C migrations)

| Table | Purpose |
|-------|---------|
| `funder_report_templates` | Post-award equivalent of `requirements_json` |
| `donor_reports` | Post-award equivalent of `proposals` |
| `uploaded_documents` | Document intake + extraction |
| `report_jobs` | Async pipeline + `agent_trace_json` |

FKs inward only: `user_id` → `users`, `linked_proposal_id` → `proposals` (nullable).

JSONB columns use `_json` suffix (locked): `report_sections_json`, `format_rules_json`, `terminology_map_json`, `knowledge_bank_json`, etc.

---

## Alembic model registration

When models are created (Stage C), uncomment imports in [`alembic/env.py`](../../alembic/env.py):

```python
# from app.reports.models.donor_report import DonorReport  # noqa: F401
# from app.reports.models.funder_report_template import FunderReportTemplate  # noqa: F401
# from app.reports.models.uploaded_document import UploadedDocument  # noqa: F401
# from app.reports.models.report_job import ReportJob  # noqa: F401
```

---

## Governance files

| File | Role |
|------|------|
| `.cursor/rules/00-global.mdc` | Spec-first discipline |
| `.cursor/rules/10-isolation.mdc` | One-way dependency |
| `.cursor/rules/20-backend.mdc` | Contract / migration parity |
| `.cursor/rules/30-agents.mdc` | Agent layer rules |
| `.cursor/rules/40-scope-fence.mdc` | Non-goals + forbidden edits |
| `.cursor/hooks.json` | Cursor hook wiring |
| `.claude/settings.json` | Claude Code hook wiring |
| `ME_MODULE_KILL_SWITCH.md` | Three kill procedures |
| `ME_MODULE_DECISION_LOG.md` | Locked decisions |

---

## Build stages (reminder)

- **Stage A** (this): governance only — no product code
- **Stage B**: spec lock — field contracts, API additions
- **Stage C**: first code — skeleton + kill-switch rehearsal on empty module
