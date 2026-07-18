# Track 3 — STOP B evidence pack (2026-07-18)

Owner-triggered prod seed + confirming walk. **No product/auth/engine fixes applied.** Anything broken is evidence.

---

## Pre-flight (re-confirmed)

| Check | Result |
|-------|--------|
| PR #8 merged | `adea209` MERGED; local `main` at tip |
| Track 3 on `main` | `b3d6d59` / `8f38a30` |
| Auth Package 1 contract citation | Linking tests docstring-cite `AUTH_AND_SSO_STRATEGY:`; normalize-via-linking assertions present |
| Auth Package 1 `app/` diff | Empty (`8f38a30..adea209`) |

---

## Step 1 — Full-row drift (read-only)

| Item | Value |
|------|-------|
| Snapshot | [`snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json`](snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json) |
| SHA256 | `64e6ebc60be775d20e451a51cd796f23e3829726c08617d8f580e8e808661afa` |
| Drift artefact | [`TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json`](TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json) |
| Divergence count | **13** |

All 13 are under `report_sections_json[*]`: missing `fact_namespaces` / `source_section_labels` on every section; missing `community_involvement.indicator_requirements`. Scalars, `format_rules_json`, and `terminology_map_json` matched committed instance.

---

## Steps 2–3 — Scoped reconcile (Option 2) + read-back

| Item | Value |
|------|-------|
| Mutation scope | `community_involvement` only: `fact_namespaces`, `source_section_labels`, `indicator_requirements` (both `elevate_on_proposal_failure: true`) |
| Version | 1 → **2** |
| Other sections / columns | Byte-identical to snapshot |
| FCDO `55f891ac-bb8b-4137-bc42-6de8ff935064` | Untouched (`sections_md5` / `row_md5` identical before/after) |
| Evidence JSON | [`TRACK3_PHASE_A_SCOPED_RECONCILE_EVIDENCE_2026-07-18.json`](TRACK3_PHASE_A_SCOPED_RECONCILE_EVIDENCE_2026-07-18.json) |
| Rollback source | Unchanged snapshot `64e6ebc6…` (not overwritten) |

---

## Step 4 — Decision log

- Table **D-055** + narrative DECISION appended in [`ME_MODULE_DECISION_LOG.md`](../ME_MODULE_DECISION_LOG.md)
- Remaining non-community drift named **O-008**

---

## Phase B — Confirming walk

### Strategies tried (deliberate degrade / unreadable)

| Strategy | Report ID | Result |
|----------|-----------|--------|
| `timeout_bait_docx` (~110k filler proposal) | `0d4e654b-f643-4d5a-ac7f-f68e1d3fab8b` | Reached Gate 1 (`awaiting_human`/`gap`) **without** checkpoint. Proposal classified `proposal`, `extraction_outcome=complete`. Duration **390.6s**. |
| `image_only_pdf_as_proposal` | `18976580-62af-4836-bdc3-9b35ee3f3f06` | Reached Gate 1 **without** checkpoint. PDF `intake_outcome=unreadable`, classified **`other`** (never proposal extract). Duration **606.5s**. |

Artefacts:

- [`TRACK3_CONFIRMING_WALK_EVIDENCE_20260718T162116Z.json`](TRACK3_CONFIRMING_WALK_EVIDENCE_20260718T162116Z.json)
- [`TRACK3_CONFIRMING_WALK_2026-07-18.log`](TRACK3_CONFIRMING_WALK_2026-07-18.log)
- [`TRACK3_CONFIRMING_WALK_DOC_CAPTURE_2026-07-18.json`](TRACK3_CONFIRMING_WALK_DOC_CAPTURE_2026-07-18.json)
- Fixtures under `audits/fixtures/`

### Checkpoint

**Not observed in prod** (continues Track 0 finding). User-facing state for both runs: `status=awaiting_human`, `stage=gap`, `proposal_checkpoint=null`. No ack/`proceed_with_gap` possible.

### Elevation / answered / skip branches

**Not executed** — blocked on checkpoint. Gate 1 captures show **zero** elevated gaps (`community_participation_examples` / `partner_or_local_collaboration_examples` absent), consistent with D-053 trigger requiring checkpoint-acked `proceed_with_gap`.

### AUTH_REFRESH_DIAG

**Zero lines** across the entire walk log (refresh path never invoked; no 401 subtype captured). Instrumentation remains live on `main` for the next long walk.

### Cost / duration (Track 2 baseline note)

| Run | Duration to Gate 1 park | Cost summary (DB capture) |
|-----|-------------------------|---------------------------|
| timeout_bait | 390.6s | `total_usd≈0.0003` (extract/reconcile only; no synthesis) |
| image_only | 606.5s | `total_usd≈0.0002` |

Full answered+skip export baseline **not obtained** (blocked upstream).

---

## Evidence classification (no fixes)

1. **Prod inducement gap (repeat of Track 0):** With live `ME_PROPOSAL_TIMEOUT_SECONDS=180`, a dense filler proposal still completes; checkpoint requires `extraction_outcome=degraded`, which did not occur.
2. **Unreadable ≠ proposal checkpoint:** Image-only PDF fails at classify (`intake_outcome=unreadable`, `classification=other`) and never enters proposal extract / `_find_degraded_proposal` (which matches only `degraded`, not `unreadable`).
3. **Track 3 elevation unconfirmed in prod** until a real `proposal_checkpoint` + `proceed_with_gap` occurs (or owner authorizes a separate inducement control, e.g. staging lower timeout — out of scope here).

---

## STOP B

Full evidence pack delivered above. **No further action.**
