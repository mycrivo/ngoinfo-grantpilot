# Gate 2 gap answers — canonical persisted shape

**Status:** Canonical (doc-only, P3-5)  
**Source of truth:** `app/reports/schemas/gate2_gap_answers.py`, `app/reports/services/gate2_gap_answer_service.py`, `app/reports/gap/gap_answer.py`  
**API surface:** `POST /api/reports/{id}/knowledge-bank/gate2/gap-responses` (§12.7a — implemented)

---

## Storage location

Persisted under `donor_reports.knowledge_bank_json.gap_answers` as a map:

```
gap_answers: { "<item_key>": Gate2GapAnswerPersisted, ... }
```

`item_key` matches E3-surfaced gap `item_key` (e.g. `performance_and_conclusions:indicator:logframe_row:op2_3`).

---

## Answered entry

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `disposition` | `"answered"` | yes | |
| `answer_text` | string | yes | Non-empty trimmed human text |
| `skip_reason` | null | yes | Must be null when answered |
| `responded_at` | ISO-8601 string | yes | Set by server |
| `provenance` | object | yes | See below |
| `source_label` | `"human_confirmed_gap_answer"` | yes | |
| `source_document_id` | uuid or null | no | Reserved; currently null |

### `provenance` (answered)

| Field | Type | Required |
|-------|------|----------|
| `source` | `"human_confirmed_gap_answer"` | yes |
| `excerpt` | string (min length 1) | yes | Same as `answer_text` at persist time |

Resolution rule (`is_gap_answer_resolved`): answered only when `provenance.source == human_confirmed_gap_answer` **and** `provenance.excerpt` is non-empty.

---

## Skipped entry

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `disposition` | `"skipped"` | yes | |
| `answer_text` | null | yes | |
| `skip_reason` | `"not_applicable"` \| `"cannot_provide"` | yes | |
| `responded_at` | ISO-8601 string | yes | |
| `provenance` | null | yes | |
| `source_label` | `"human_confirmed_gap_answer"` | yes | |
| `source_document_id` | null | yes | |

---

## Gate unlock

- `gate2_confirmed_at` is set when **every** E3-surfaced gap has a resolved entry (answered or skipped).
- Partial submit clears any prior `gate2_confirmed_at` until all gaps resolved.
- Unknown `item_key` in request → `422 GATE2_UNKNOWN_GAP_KEYS`.

---

## Non-canonical / provisional

| Surface | Status |
|---------|--------|
| `PATCH /api/reports/{id}/gap-answers` (§12.7) | **PROVISIONAL** — not implemented; do not build UI against this shape |
| Legacy entries with `answer_text` but no `provenance` | **Not resolved** — rejected by `is_gap_answer_resolved` |

**Code alignment backlog:** Implement or remove §12.7 PATCH route; align any legacy gap-answer writers to this contract (`ME_MODULE_FOLLOWUP_BACKLOG.md` → P-UX-11).
