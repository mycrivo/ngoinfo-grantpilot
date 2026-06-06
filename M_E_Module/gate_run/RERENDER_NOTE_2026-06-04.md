# Re-render note — 2026-06-04

## Guards

| # | Check | Result |
|---|--------|--------|
| 1 | Production target | **PASS** — Railway project **NGOINfo-GrantPilot AI**, environment **production** |
| 2 | Deploy includes render fix | **PASS** — SHA **`6fa9153bcf98b4302d267a36d7658bf043261f3b`** (`6fa9153`); Railway backend deployment **`bce97271-0ed9-4759-90c4-e2ecb2c39d41`** SUCCESS 2026-06-04 17:10 UTC+1 |
| 3 | Pre-check on `6643d922` | **PASS** — status `COMPLETE`, gate3 set, 8 sections / 6 with prose, old export pointer present |

## Export run

- **Mechanism:** `export_and_persist()` only (same render path as `_run_export_stage`; no pipeline walk, no Gate 3 re-confirm)
- **Old `storage_ref`:** `users/0efd525e-bca1-4142-b748-c99b5f52b1b8/reports/6643d922-150d-4000-b878-4025e7c9145a/cdd24bb0-0fae-40a3-b7cc-19e8fe493286/Foreign_Commonwealth_Development_Office_FCDO_Annual_Review_2025-04-01_2026-03-31.docx`
- **New `storage_ref`:** `users/0efd525e-bca1-4142-b748-c99b5f52b1b8/reports/6643d922-150d-4000-b878-4025e7c9145a/a20bad7c-3260-43fe-b9aa-ecc95217fd73/Foreign_Commonwealth_Development_Office_FCDO_Annual_Review_2025-04-01_2026-03-31.docx`
- **Post-export status:** **`COMPLETE`** (not DEGRADED)
- **Bytes:** 44,179 (`render_mode: from_scratch`)

## Body-text assertions (Normal-style paragraphs only)

| Check | Result |
|--------|--------|
| Contains `Risk management` | **PASS** |
| Contains `did not report` | **PASS** |
| Contains `against a budget of` | **PASS** |
| Contains `fell below milestone` | **PASS** |
| Contains `clear limitations` | **PASS** |
| Body lacks `Risk rating / assumptions / controls` | **PASS** (phrase appears in H1/H2 labels only — expected terminology-on-labels) |
| Body lacks `Budget / forecast and actual costs` | **PASS** |
| Body lacks `did not Annual Review` | **PASS** |
| No orphan `[ [` / `[ ]` runs | **PASS** |
| No `fact:` / `gap:` / `ARCH_` / section-key leaks | **PASS** |

## Heading-label check

- **PASS** — Section H1 `Risk, Assumptions and Safeguarding` → `Risk rating / assumptions / controls, Assumptions and Safeguarding`; table H2 `Risk update` → `Risk rating / assumptions / controls update`. Other FCDO section labels present (e.g. `A. Summary and Overview`, `B. Performance and Conclusions`).

## Section coverage (8 template sections)

| Section | Render |
|---------|--------|
| `summary_and_overview` | prose |
| `performance_and_conclusions` | prose |
| `detailed_output_scoring` | `[Section not generated]` placeholder (known — synthesis failed) |
| `evidence_and_evaluation` | prose |
| `risk_and_safeguarding` | prose |
| `value_for_money` | `[Section not generated]` placeholder (known — synthesis failed) |
| `programme_management_delivery_commercial_financial` | prose |
| `recommendations_and_actions` | prose |

## Deliverables

- `6643d922_export_v2.docx` — new fixed render (original `6643d922_export.docx` unchanged for before/after)
