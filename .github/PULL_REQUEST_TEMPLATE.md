## Package
- ID / title:
- Tier: GREEN | AMBER | OWNER
- Spec: `docs/packages/<ID>.md`
- Fence declared vs files touched (list any file outside the fence):

## Contract lines implemented
| Contract § | What | Pointer (file, symbol) |
|---|---|---|

## Tests
- `pytest tests/contract/<ID>/ -q` → last line:
- `pytest tests/ -q` → last line:
- Guard → last line:
- New unit tests added (paths):

## Migration (or "none")
- Revision id:
- `alembic upgrade head` / `alembic downgrade -1` / `alembic upgrade head` → proof lines:
- Backfill idempotent and reversible: yes / no / n.a.

## Proposed test changes (not edited)
| Test | Why it is believed wrong |
|---|---|

## Not done
What the spec asked for that this PR does not deliver, and why.

## Owner-triggered verification
Exact commands for the live fixture run / harness / DOCX read, if the spec requires them.

## Decisions
Locked decisions touched (should be none) · new decisions proposed (with a one-line rationale).

## Audit
- [ ] Bugbot review complete, findings addressed or answered
- [ ] Claude Code audit attached (link) — no BLOCKER
- [ ] Owner live run recorded (scorecard same-or-better on Layers 1, 4, 5; DOCX read)
