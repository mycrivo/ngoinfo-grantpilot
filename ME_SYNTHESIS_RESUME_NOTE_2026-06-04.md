# F1 synthesis resume (2026-06-04)

**Skip rule:** Regenerate only when a section is missing, `generation_status == "FAILED"`, or `content.text` is empty. Skip (carry forward unchanged) when `human_edited == True`, `generation_status == "ACCEPTED"`, or status is `GENERATED` / `AWAITING_REVIEW` with non-empty text — ambiguous cases skip.

**Merge:** `merge_synthesis_sections` + `merge_content_json_after_synthesis` walk template order, apply fresh results for regenerated keys only, preserve existing sections (prose, `critic_flags`, status) byte-for-byte; sibling top-level keys (`export`, gate stamps) retained via shallow copy of prior `content_json`.

**DEGRADED:** `report.status = DEGRADED` when merged `generation_summary.failed > 0`; clears to `DRAFT` when failures reach zero. Single end-of-run commit unchanged.

**Untouched:** payload trim, timeout/retry, `ME_SYNTHESIS_MAX_CONCURRENCY=2`, F2, Gate 3, renderer. `test_idempotent_overwrite` replaced by resume/skip tests.
