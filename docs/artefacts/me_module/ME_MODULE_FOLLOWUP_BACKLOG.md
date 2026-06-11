# M&E module — follow-up backlog (post failed-journey fix)

Items identified during the failed-report UX audit (2026-06-07). Each is a separate scoped task.

> **ID collision note (P3-5):** Rows below use **`P-UX-*`** IDs for UX/product backlog items. These are **distinct** from Phase 3 plan packages **`P3-1`…`P3-6`** in `phase_3_durable_engine_58dec94c.plan.md` (eval harness, worker recovery, output quality, etc.).

| ID | Issue | Suggested direction | Priority |
|----|--------|---------------------|----------|
| P-UX-1 | Orphaned `running` jobs after worker crash | Worker startup reclaims stale `running` rows → `failed` + quota refund | High — see Phase 3 **P3-2** |
| P-UX-2 | `donor_reports.status` not synced during pipeline | Prefer `latest_job_status` on list (done); optional worker status sync | Low |
| P-UX-3 | Stage-specific failure headlines | `resolveReportFailureHeadline(stage)` for drafting/export failures | Medium |
| P-UX-4 | No document delete/replace API | `DELETE /api/reports/{id}/documents/{doc_id}` + upload UI | High — **Live** (P6); UI may remain |
| P-UX-5 | Wrong format preflight on upload | Block `.docx` for `indicator_data` before enqueue | Medium |
| P-UX-6 | Holding state for DRAFT + no job | Route to `upload` instead of indefinite reading holding | Medium |
| P-UX-7 | Sentinel `__default__` reports in list | Filter from list or show archived label | Low |
| P-UX-8 | Upload enqueue redirects to list | After enqueue, push to `/reports/{id}/reading` | Low |
| P-UX-9 | No report delete | `DELETE /api/reports/{id}` for DRAFT + failed only | Medium |
| P-UX-10 | Contract drift on quota timing | Align API_CONTRACT §12.8 with create+refund-on-failure model | Done via D-050 |
| P-UX-11 | Gap-answers PATCH §12.7 vs canonical §12.7a | Align or remove provisional PATCH route; enforce `Gate2GapAnswerPersisted` everywhere | Medium — doc canonical in `GATE2_GAP_ANSWERS_FIELD_CONTRACT.md` (P3-5) |
