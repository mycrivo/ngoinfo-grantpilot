# DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS_V2_DELTA.md

**Status:** Canonical (LOCKED for V2 build) — applies **on top of** `DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS.md` v1. Where they conflict, this delta wins.  
**Applies to:** M&E Module — document intake V2  
**Migration:** same revision as `grants` (additive).  
**Decisions:** D-084, D-086

---

## 1. What changes

| v1 | V2 |
|---|---|
| Document belongs to a report only | Document belongs to a **grant** and (for beta) to the report it was uploaded in |
| `classification` set only by the classifier | `classification` may be **declared by the user** at upload or **set by the system** (discovery); the classifier runs only when neither |
| Seven classification values | Values extended for funder guidance, logframe, finance, prior report, feedback |
| Every classified document feeds fact extraction | `funder_guidance` and `funder_feedback` **never** enter the knowledge bank |

---

## 2. New / changed columns on `uploaded_documents`

| DB column | Python attribute | Type | Null | Default | Constraints |
|---|---|---|---|---|---|
| `grant_id` | `grant_id` | UUID | YES* | NULL | FK → `grants.id`, ON DELETE CASCADE. *NULL only for pre-V2 rows until backfill |
| `classification_source` | `classification_source` | TEXT | NO | `'classifier'` | CHECK: `user | classifier | system` |
| `source_url` | `source_url` | TEXT | YES | NULL | Set when the file was fetched by discovery |
| `fetched_at` | `fetched_at` | TIMESTAMPTZ | YES | NULL | Set when fetched by discovery |

`donor_report_id` stays NOT NULL in beta (every upload happens inside a report). The next-report workflow (post-beta) will relax it.

---

## 3. `classification` values (ENUM_REGISTRY §5.3 extension — additive)

| Value | Meaning | Routed to |
|---|---|---|
| `funder_guidance` | The funder's reporting template, guidance note, or the reporting clause extract used as the governing document | Requirement compiler only. **Never** fact extraction. |
| `proposal` | Winning proposal / application | Proposal extractor |
| `grant_letter` | Award letter / grant agreement / contract | Grant terms extractor (also read by the compiler for reporting-clause fallback) |
| `logframe` | Logical framework / results framework document | Indicator lane (structured grid where available) |
| `indicator_data` | Monitoring sheet / indicator tracker (xlsx, csv, docx table) | Indicator lane |
| `finance` | Budget vs actual, expenditure statement | Finance lane (text or grid) |
| `prior_report` | A previously submitted report for this grant | Text lane; facts carry the prior period and `source.kind = document` |
| `funder_feedback` | Funder comments/letters on a prior report | **Reserved.** Stored, not routed in beta |
| `management_action` | Management response / action tracker | **Reserved.** Stored, not routed in beta |
| `mou` | Memorandum of understanding | Text lane |
| `photo` | Image evidence | Not routed (unchanged) |
| `deck` | Presentation | Text lane (unchanged) |
| `other` | Unclassified | Text lane |

**Rules**
- A `role` supplied at upload (`API_CONTRACT_ME_V2.md` §12.3) sets `classification` with `classification_source = user`; the classifier is skipped for that document.
- Documents fetched by discovery are inserted with `classification = funder_guidance`, `classification_source = system`, `source_url`, `fetched_at`.
- The classifier may assign any non-reserved value except `funder_guidance` (a funder document is a user or system decision, never a guess — a guess here would let a template be silently applied, which D-086 forbids). If the classifier believes a document is a funder template, it assigns `other` and the intake surfaces a hint to the NGO.
- `extraction_status` semantics unchanged; for `funder_guidance` it tracks compilation input readiness (`COMPLETE` = text and tables available to the compiler).

---

## 4. `extracted_json` addition

```json
{
  "extractor_agent": "string",
  "extracted_at": "ISO-8601 or null",
  "raw_text_ref": "string or null",
  "tables_ref": "string or null — structured tables from Docling where available",
  "structured": {},
  "facts_emitted": ["fact_key"],
  "period_hints": [ { "label": "string", "start": "date or null", "end": "date or null", "where": "string" } ],
  "confidence": "number 0–1 or null",
  "degrade": { "code": "string or null", "message": "string or null — user language" },
  "error": "string or null"
}
```

- `facts_emitted` lists every fact key this document contributed, so a document can be traced to its facts and, on delete, its facts superseded.
- `period_hints` are the periods the extractor recognised in the document (headers like "Year 1", "Apr 2025–Mar 2026"); the reconciler uses them to populate `ledger.periods`.

---

## 5. Backfill (P2.1)

Set `grant_id` from the parent report's `grant_id`. Set `classification_source = classifier` for all existing rows. Reversible.

---

## 6. Indexes (additions)

| Index | Purpose |
|---|---|
| `(grant_id, classification)` | Documents for a grant by role (next-report seed) |

---

## 7. Build Enforcement

Invalid and must not be merged:
- any fact in a knowledge bank whose `source.document_id` is a `funder_guidance` or `funder_feedback` document;
- the classifier assigning `funder_guidance`;
- a discovery-fetched document without `source_url` and `fetched_at`;
- an upload with a user-supplied role that still runs the classifier.
