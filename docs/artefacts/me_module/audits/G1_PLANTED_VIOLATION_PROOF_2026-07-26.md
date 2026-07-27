# G1 planted-violation proof transcript


## 1. Funder string on engine path

denied=True
Governance guard denied the write:
- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.
- [funder_fixture] app/reports/gap/planted.py: blocklisted token 'FCDO' | line: label = "FCDO Annual Review"

## 2. Bare fixture number in prompt component

prompt_denied=True
non_prompt_bare_denied=False (expect False)

## 3. Unflagged protected-file edit

denied_without_override=True
allowed_with_override=True

## 4. Engine importing harness

denied=True
Governance guard denied the write:
- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.
- [harness_import] app/reports/services/x.py: engine must never import app.reports.eval (harness may import engine; one-way only; no override)

## 5. Fake secret

denied=True

## 6. Deletion never fires

added=['label="generic"']
denied=False (expect False)

## 7. PreToolUse funder deny (stdin simulation)

exit=2
{"permission": "deny", "user_message": "Governance guard denied the write:\n- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.\n- [funder_fixture] app/reports/gap/x.py: blocklisted token 'FCDO' | line: x = \"FCDO Annual Review\"", "agent_message": "Governance guard denied the write:\n- THE BOUNDARY (AGENTS.md): Nowhere, ever: funder names, slugs, expected counts, or quoted fixture phrases in engine code or prompts. Docs don't govern; gates govern.\n- [funder_fixture] app/reports/gap/x.py: blocklisted token 'FCDO' | line: x = \"FCDO Annual Review\""}
