# AGENTS.md — GrantPilot Engine Constitution (distilled)
Ratified 2026-07-26 (D-065). Full text: docs/artefacts/me_module/ME_ENGINE_BEHAVIOURAL_CONTRACT_v1.0.md. Enforced by hooks and the CI eval gate, not by memory. Machine-loaded by all build and audit agents.

THE LAW. The engine's judgment is universal; the funder's demands are data; the report is the universal judgment shaped by that data. Everything the engine knows is M&E domain knowledge. Everything a funder wants lives in template data. Adding or retiring a funder never touches engine code or prompts.

THE BOUNDARY. Engine code and prompts may contain: the fact ontology, the six behaviours, honesty invariants, universal M&E knowledge. Template data may contain: structure, labels, limits, tone, requirement declarations in ontology vocabulary, table definitions, exclusions, disclosure rules. Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts; no substring hint maps; no archetype guessing. A template that under-declares fails loudly at validation — the engine never compensates silently at run time.

THE SIX BEHAVIOURS. B1 read whole, read once, into the typed ontology — never per-document narrow schemas. B2 validate deterministically in pure code — findings attach as caveats, never silently alter values. B3 reconcile, never resolve — conflicts exist only within the same ontology slot; "both are true" is a legitimate resolution; superseded values persist as history. B4 gaps are semantic — a requirement is satisfied only by the right slot and facet; never ask what the ledger holds, what is funder-owned, or what the template doesn't require. B5 write honestly from the confirmed ledger and the whole template — every claim binds to a fact or an answer; empty means a short honest section, never off-topic padding; caveats survive into prose; no internal identifiers reach a user. B6 verify meaning, not tokens — dates as dates, numbers normalized, derivations recomputed; flag floods are themselves defects.

HONESTY INVARIANTS. Absence is a first-class object. A nil return is a statement; missing information is not a nil return. insufficient_data and DEGRADED over invention, always. Silent impoverishment — the user unknowingly receiving less than the documents support — is the named enemy, including its costume: off-topic filler.

BUILD DISCIPLINE. Build only from versioned package specs — never from chat. Plan-first; AMBER packages STOP for owner approval before execution. One scoped package at a time. The builder never certifies: certification is the harness scorecard plus independent review. Regressions are reverted or bisected, never fixed forward. Tests and thresholds are never weakened to force green; baselines move only by explicit, singular, owner-signed decision recorded in the decision log.

MERGE RULE. No engine-path merge below same-or-better on all five BridgeLight layers plus the sealed pack. Assertions are two classes: invariant (forbidden outputs, honesty behaviours — never relaxed; a pass that exists only because upstream data was missing records PASS-BY-STARVATION and is not a safety property) and baselined (floor = recorded baseline with commit SHA, dataset version, model config).

DUTIES. Every stage persists its inputs and outputs — nothing undiagnosable by design. Every eval report prints its lineage. Protected files (goldens, this file, the contract, hook configs) are guarded; overrides are flagged, logged, and visible in review. The sealed fixture is never quoted anywhere outside the harness.

This file is also read by every coding agent (Cursor agents and subagents, cloud agents, Claude Code). Package specs, contracts and the master task list say *what* to build; the constitution above and the sections below say *how*.

## 1. What this repository is

FastAPI backend for GrantPilot (Fit Scan, Proposal Writer, M&E Report Writer). PostgreSQL on Railway. The M&E module lives under `app/reports/` and is isolated: M&E may depend on GrantPilot core; core never depends on M&E. Proposal, Fit Scan, auth, billing and security behaviour are never altered by M&E work.

Frontend is a separate repository (`grantpilot-frontend`, Next.js).

## 2. Where the truth lives

| Question | Read |
|---|---|
| What are we building, in order | `docs/ME_V2_MASTER_TASK_LIST.md` |
| The package I am working on | `docs/packages/<ID>.md` (one file per package; the spec is the file, not the chat) |
| Data shapes | `docs/DB_FIELD_CONTRACT_GRANTS.md`, `docs/DB_FIELD_CONTRACT_DONOR_REPORTS_V2_DELTA.md`, `docs/DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS_V2_DELTA.md`, `docs/REPORT_REQUIREMENT_SNAPSHOT_SCHEMA.md` |
| API shapes | `docs/API_CONTRACT_ME_V2.md` (§12 v2), `docs/artefacts/API_CONTRACT.md` (§1–§11) |
| Enums | `docs/artefacts/ENUM_REGISTRY.md` |
| Decisions already taken | `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md` — locked decisions are not reopened |
| Runtime and security rules | `docs/artefacts/GUARDRAILS_RUNTIME_AND_SECURITY.md` |
| Behavioural contract (full) | `docs/artefacts/me_module/ME_ENGINE_BEHAVIOURAL_CONTRACT_v1.0.md` |

Documents describe intent; code and CI define reality. When they disagree, say so in the PR; do not silently reconcile.

## 3. Commands

Run from the repository root with the virtual environment active.

| Purpose | Command |
|---|---|
| Install | `pip install -r requirements.txt` |
| Tests (CI tier — no model calls, no network) | `pytest tests/ -q` |
| Contract tests only | `pytest tests/contract/ -q` |
| Migrations | `alembic upgrade head` · downgrade one: `alembic downgrade -1` |
| Funder-string guard (tree-wide) | `python scripts/governance/tree_audit.py` |
| Funder-string guard (staged / pre-commit) | `python scripts/governance/run_guards.py --staged --layer pre-commit --allow-env-override` |
| Harness: export a run bundle | `pytest tests/test_p0_bundle_export_scorecard.py -q` (CI-tier constructed inputs). Owner-triggered production read: `python scripts/audit/bundle_export_run.py --railway --out <path>` — do not run that from an agent. |
| Harness: score a bundle | `python scripts/audit/scorecard_emit.py --bundle <path>` (local already-exported bundle only; no production) |
| Run the API locally | `uvicorn app.main:app --reload` |

A command in this table that does not run is a defect in this file; fix the table in the same PR.

Agents run the **CI tier** only. Anything that calls a model, touches Railway, Stripe, object storage or a production database is **OWNER-TRIGGERED**: propose the exact command and stop.

## 4. The build law (additions; does not replace BUILD DISCIPLINE)

1. **Contract before code.** A package's contract lines are final before implementation starts. If the spec conflicts with a contract, STOP and report the conflict; do not code around it.
2. **Tiers.** GREEN — proceed inside the package fence. AMBER — anything touching the moat (extraction, reconciliation, requirements, evidence matrix, synthesis, critic), schema, quota, auth or the live user journey: produce a plan first and stop for approval. OWNER — production mutations and live validation: propose, never execute.
3. **Tests are the ruler.** Tests under `tests/contract/` are written by the `contract-tester` subagent from the contracts and the package's acceptance lines. The implementer may not edit them. A test believed wrong is listed in the PR description under "Proposed test changes" with the reason; a human decides.
4. **Anti-bent-ruler.** Never change an assertion to match behaviour. A target moves only when the correct answer has changed, and every moved target is listed in the PR. This restates BUILD DISCIPLINE; it does not relax it.
5. **Anti-death-star.** One package, one fence. If the fence must grow, stop and say why.
6. **No fixture vocabulary.** No funder name, fixture organisation, fixture phrase or expected count in any prompt, engine file or test that asserts engine behaviour. The guard blocks it; do not work around the guard.
7. **Evidence, not inference.** A claim in a PR description carries a pointer (file, symbol, test name). "Should work" is not a status.
8. **Rollback path.** Schema changes are additive and reversible; old read paths stay readable until the documented cutover.
9. **Kill switch untouched.** `ME_MODULE_ENABLED`, the frontend flag and the worker switch keep working at every commit.
10. **Secrets.** Never print, log, commit or paste a secret value. Key names only. `.env*` files are never read into context.

Agent-side hooks are wired but not observed to fire in Cursor 3; `scripts/governance/run_guards.py` via `.githooks/pre-commit` is the enforcing layer.

## 5. M&E engine rules (apply under `app/reports/`)

These do not replace THE LAW, THE BOUNDARY or THE SIX BEHAVIOURS.

- Structure for a report comes from that report's **requirement snapshot**. `funder_report_templates` is retired as an engine read (rows kept; no engine reads from P3 onward). Funder demands remain data, not code.
- Facts follow the V2 fact shape and key grammar in `docs/DB_FIELD_CONTRACT_GRANTS.md` §3: facet, period, scope, entity, provenance, supersession. Milestone and endline target are different facts.
- **Derived numbers are computed by code.** A model never performs arithmetic; the writer cites derived facts. This restates B2 and B6; it does not relax them.
- The **evidence matrix** is the only satisfaction judgement. Gates, writer and critic read it; nothing re-judges. This restates B4; it does not relax it.
- Gate conversations mutate state **only through recorded actions** with an echo. Free text is never stored as a fact.
- Every enum returned by an API carries a `_label` sibling in user language.
- A money fact without currency is unconfirmed by definition.
- Generic structure is fallback only; never blended into a funder-specific snapshot.

## 6. Pull requests

Use `.github/PULL_REQUEST_TEMPLATE.md`. Every PR states: package ID and tier; contract lines implemented; tests added under `tests/contract/` and `tests/`; proposed test changes (if any); guard result; migration up/down proof (if any); what was **not** done and why. Bugbot reviews every PR. Claude Code audits every package before merge. The owner merges; nobody else. MERGE RULE above still governs engine-path merges.

## 7. Style and isolation

Match the existing code. Service layer owns business rules and transactions; route handlers validate and delegate; models carry no business logic. snake_case JSON. No new patterns without a reason stated in the PR.

- Diagnose before fixing — structured root-cause before any patch.
- Backend is source of truth: entitlements, gates and AI live server-side. The frontend repo renders and calls the API; adapt UI to contract, never reverse.
- Locked or revised choices go in `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md`. Append; do not silently pivot.
- Isolation: `app/reports/` may import core; core must never import `app.reports` (enforced by `.cursor/hooks/isolation_veto.py`). The only core mount is `app/main.py` behind `ME_MODULE_ENABLED`. FKs inward only; no core migration alters core tables for M&E. Worker scale-to-0 is the runtime kill switch.
- Do not modify `app/services/export_service.py`, `app/services/proposal_service.py`, `app/api/routes/proposals.py`, or `app/ai/prompts/proposal.py` for M&E work.
- Non-goals (stop if a prompt drifts here): field-data collection, dashboards, a live logframe/ToC system, real-time monitoring, multi-user approval workflows, Level-3 open-ended autonomy, Railway per-session sandboxes, building Docling / Agent SDK / Word engines from scratch.
