# G1 planted-violation proof transcript

Per D-077: a guard is not in force until a planted violation is observed blocked at each layer it claims to cover. Library-level calls are labelled and do **not** count as layer proofs.

CI proof run URL (filled after --no-verify plant): see section **Layer: CI**.


## Layer: library (not a layer proof)

funder denied=True (library only)

## Layer: PreToolUse

funder_fixture PreToolUse exit=2
`{"permission": "deny", "user_message": "Governance guard denied the write:\n- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.\n- [funder_fixture] app/reports/gap/x.py: blocklisted token 'FCDO' | line: x = \"FCDO Annual Review\"", "agent_message": "Governance guard denied the write:\n- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.\n- [funder_fixture] app/reports/gap/x.py: blocklisted token 'FCDO' | line: x = \"FCDO Annual Review\""}`

secret_write on docs/ PreToolUse exit=2
`{"permission": "deny", "user_message": "Governance guard denied the write:\n- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.\n- [secret] docs/artefacts/me_module/audits/_planted_secret.md: possible secret pattern: sk-[A-Za-z0-9]{20,} | line: k=\"sk-<planted-fake-redacted>\"", "agent_message": "Governance guard denied the write:\n- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.\n- [secret] docs/artefacts/me_module/audits/_planted_secret.md: possible secret pattern: sk-[A-Za-z0-9]{20,} | line: k=\"sk-<planted-fake-redacted>\""}`

## Layer: pre-commit (staged via run_guards.py --staged)

### pre-commit / staged — funder string on engine path (expect deny)

exit=1
```
Governance guard denied the write:
- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.
- [funder_fixture] app/reports/gap/_g1_plant.py: blocklisted token 'FCDO' | line: x = "FCDO Annual Review"
```

### pre-commit / staged — harness import from engine path (expect deny)

exit=1
```
Governance guard denied the write:
- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.
- [harness_import] app/reports/services/_g1_plant.py: engine must never import app.reports.eval (harness may import engine; one-way only; no override) | line: from app.reports.eval.gates import gate_faithfulness
```

### pre-commit / staged — unflagged protected write (expect deny)

exit=1
```
Governance guard denied the write:
- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.
- [protected_file] AGENTS.md: protected file write requires explicit override: set env GOVERNANCE_OVERRIDE=<reason> for pre-commit/PreToolUse; also put GOVERNANCE_OVERRIDE: <reason> in the commit message for CI
```

### pre-commit / staged — protected write with GOVERNANCE_OVERRIDE (expect allow + log entry)

exit=0
```
governance: override path=AGENTS.md reason='g1-proof-transcript-precommit'
```

Override log entries appended by allow path:
```
{"timestamp": "2026-07-27T12:26:46.706725+00:00", "actor": "unknown", "path": "AGENTS.md", "reason": "g1-proof-transcript-precommit", "layer": "pre-commit"}
```

### pre-commit / staged — deletion of blocklisted string (expect allow)

exit=0
governance: OK


## Layer: CI

Planted funder-string commit with `git commit --no-verify` (`c2b1958` → tip `7284b6b` still containing `app/reports/gap/_g1_ci_plant.py`), push, observed `governance-guards` exit non-zero, then revert in the next commit.

**Job URL:** https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/30266529052/job/89978423265  
**Run:** https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/30266529052  
**Conclusion:** failure (exit code 1)

Log excerpt:

```
Run unset GOVERNANCE_OVERRIDE || true
python scripts/governance/run_guards.py --range "$RANGE" --layer ci
…
Governance guard denied the write:
- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.
- [funder_fixture] app/reports/gap/_g1_ci_plant.py: blocklisted token 'FCDO' | line: x = "FCDO Annual Review"
##[error]Process completed with exit code 1.
```

CI also rendered per-commit override reasons in the same job (every protected-path override in the merge-base..head range, not last-only).
