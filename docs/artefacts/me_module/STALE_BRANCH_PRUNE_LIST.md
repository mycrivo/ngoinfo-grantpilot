# STALE_BRANCH_PRUNE_LIST.md

**Status:** Owner sign-off list only — **no branches deleted in Package H0**.  
**Generated:** 2026-07-26  
**Scope:** Remote branches on `origin` not merged into `origin/main`.  
**Method:** `git for-each-ref refs/remotes/origin` minus `git branch -r --merged origin/main` (excludes `origin/main` and the bare `origin` remote-tracking alias).

| Last commit | Branch | One-line description | Recommendation | Rationale |
|---|---|---|---|---|
| 2026-02-04 | `claude/audit-grantpilot-backend-bMXL4` | Add comprehensive backend audit report (2026-02-04) | **delete** | Stale audit artefact branch; content not on main |
| 2026-02-15 | `claude/audit-google-oauth-PXTlp` | Add comprehensive security & vulnerability audit report | **delete** | Stale audit artefact branch |
| 2026-02-15 | `feat/frontend-bootstrap-design-system` | Frontend: bootstrap Next.js app skeleton and brand system | **delete** | Historical frontend bootstrap; product frontend lives in separate repo |
| 2026-02-22 | `docs/defer-dashboard-lists-mvp` | docs: defer dashboard lists; align frontend MVP; fix export verb | **delete** | Stale docs/MVP alignment branch |
| 2026-02-23 | `for-claude-code-review` | Add files via upload | **delete** | Ad-hoc upload branch; no ongoing work |
| 2026-03-03 | `claude/audit-onboarding-pipeline-ImpDv` | docs(audit): full onboarding pipeline audit 2026-03-03 | **delete** | Stale audit artefact branch |
| 2026-03-09 | `claude/test-grantpilot-backend-57YvD` | Add backend smoke test report with field name mismatch findings | **delete** | Stale test/report branch |
| 2026-03-23 | `claude/smoke-test-grantpilot-m343C` | Add GrantPilot end-to-end smoke test script | **delete** | Stale smoke-test branch |
| 2026-06-02 | `claude/zen-sagan-HppBG` | docs(me-r0): KB consumer seam audit for fact/gap key canonicalisation | **delete** | Stale M&E audit branch |
| 2026-06-06 | `claude/nice-wright-nhtcP` | docs(me): make Screen 3 funder picker a searchable combobox | **delete** | Stale frontend-doc branch |
| 2026-06-08 | `claude/sharp-euler-e4chi3` | Add M&E static audit findings handoff | **delete** | Stale audit handoff branch |
| 2026-06-09 | `claude/nifty-cerf-x365du` | Add clean rebuild of NGOInfo home page body content | **delete** | Stale marketing/home page branch |
| 2026-06-14 | `claude/eager-planck-vt2d49` | Add read-only M&E output-quality & integrity audit (2026-06-14) | **delete** | Stale M&E audit branch |
| 2026-07-19 | `feat/gate1-conflict-integrity` | docs(me): quote fix round 2 CI PASSED lines | **keep** | Package 1 feature lineage; keep until Package 1 Phase C/D closes |
| 2026-07-20 | `claude/package-1-prs-audit-l57vt5` | docs(me): delta re-audit #2 final — merge-ready verdict pinned to 340cc7f | **keep** | Package 1 audit evidence branch; keep until Package 1 closes |

**Count:** 15 unmerged remote branches (13 delete-recommended, 2 keep-recommended).

## Sign-off

- [ ] Owner approved delete set
- [ ] Owner confirmed keep set
- [ ] Deletions executed in a later chore (not H0)
