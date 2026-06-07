# M&E module — follow-up backlog (post failed-journey fix)

Items identified during the failed-report UX audit (2026-06-07). Each is a separate scoped task.

| ID | Issue | Suggested direction | Priority |
|----|--------|---------------------|----------|
| P3-1 | Orphaned `running` jobs after worker crash | Worker startup reclaims stale `running` rows → `failed` + quota refund | High |
| P3-2 | `donor_reports.status` not synced during pipeline | Prefer `latest_job_status` on list (done); optional worker status sync | Low |
| P3-3 | Stage-specific failure headlines | `resolveReportFailureHeadline(stage)` for drafting/export failures | Medium |
| P3-4 | No document delete/replace API | `DELETE /api/reports/{id}/documents/{doc_id}` + upload UI | High |
| P3-5 | Wrong format preflight on upload | Block `.docx` for `indicator_data` before enqueue | Medium |
| P3-6 | Holding state for DRAFT + no job | Route to `upload` instead of indefinite reading holding | Medium |
| P3-7 | Sentinel `__default__` reports in list | Filter from list or show archived label | Low |
| P3-8 | Upload enqueue redirects to list | After enqueue, push to `/reports/{id}/reading` | Low |
| P3-9 | No report delete | `DELETE /api/reports/{id}` for DRAFT + failed only | Medium |
| P3-10 | Contract drift on quota timing | Align API_CONTRACT §12.8 with create+refund-on-failure model | Done via D-050 |
