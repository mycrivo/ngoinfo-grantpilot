# Claude Code — auditor-side wrapper

**Mandatory read:** [`AGENTS.md`](AGENTS.md) — GrantPilot Engine Constitution (distilled). Do not duplicate constitution text here.

Conventional backend (services, models, migrations, routes, docxtpl) is Cursor's domain. Claude Code owns auditor-side work against `app/reports/agents/`, gate hooks, and agent-trace plumbing when asked. Builder charter lives in `.cursor/rules/00-global.mdc`.

## Orientation (spec detail)

1. `docs/artefacts/me_module/ME_MODULE_MASTER_MEMORY.md` §7.3–7.5 — roster, pipeline, execution
2. `docs/artefacts/me_module/REPO_MAP_ME_MODULE.md` — where code lives
3. `docs/artefacts/me_module/ME_MODULE_ARCHITECTURE_SPEC.md` §B3–B5 — model strategy, cost ceiling
4. `docs/artefacts/ENUM_REGISTRY.md` §5 — agent output enums (e.g. classifier → §5.3)

Builder reference tables (agent roster; historical model-class routing) live in `.cursor/rules/30-agents.mdc`.

## Charters

Role charters (BLOCK B): `.claude/agents/{auditor,harness-runner,security-reviewer,ngo-reviewer,adjudicator}.md`. Builder charter: `.cursor/rules/00-global.mdc`.

## Harness invocation

Pending — harness-runner charter exists; headless CI invocation lands with the harness package. Until then, do not invent a CLI.

## Repo hazards (isolation)

- All agent code under `app/reports/agents/`; worker under `app/reports/worker/`.
- **Import core; never be imported by core.** Hooks in `.claude/hooks/` enforce this (and must be proved live — see D-077).
- Do not edit `app/services/`, core `app/api/routes/`, or proposal/export paths.
- Agents run in the **background worker** via `run_pipeline(report_id)` — never block HTTP handlers.

## Reuse from core (import only)

- `app.integrations.openai_client` — synthesis path only
- `app.ai.prompt_runner` / humaniser patterns — section writing
- `app.services.profile_service` — NGO context
- `app/reports/extraction/docling_adapter.py` — Layer 1 text (classifier consumes metadata/text, not Docling directly unless needed)

Do **not** duplicate billing, auth, or quota logic inside agents — call services when needed.

## Hooks

`.claude/settings.json` and `.cursor/hooks.json` wire PreToolUse guards (isolation veto, funder/fixture string, protected-file, harness-import, secret write) and PostToolUse migration parity. Shared logic: `.cursor/hooks/`. Pre-commit: `.githooks/pre-commit`. CI: `governance-guards` job in `.github/workflows/smoke-test.yml`.

## When unsure

Append to `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` and stop — do not guess on contracts (Stage B locks field shapes).
