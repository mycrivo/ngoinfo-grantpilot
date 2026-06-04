# DB_FIELD_CONTRACT_UPLOADED_DOCUMENTS.md

**Status:** Canonical (LOCKED — Stage B structure)  
**Applies to:** M&E Module — document intake  
**System of Record:** Railway PostgreSQL + Railway Buckets (object storage)  
**Owner:** M&E Module / Backend  
**Migration:** Migrations `0014_me_module_tables` + `0015_donor_reports_gap_analysis_json` applied; alembic head = `0015_gap_analysis_json`; deployed to production.

---

## 1. Purpose

This contract defines persistence for **uploaded documents** — the M&E ingestion surface.

Each row represents one file uploaded against a donor report:
- Binary stored in object storage (`storage_ref`)
- Metadata and classification in PostgreSQL
- Structured extraction output in `extracted_json`

---

## 2. Table: `uploaded_documents`

### 2.1 Identity & Ownership

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `id` | `id` | UUID | NO | `gen_random_uuid()` | PRIMARY KEY |
| `donor_report_id` | `donor_report_id` | UUID | NO | — | FK → `donor_reports.id`, ON DELETE CASCADE |
| `user_id` | `user_id` | UUID | NO | — | FK → `users.id`, ON DELETE CASCADE |

**Rules**
- `user_id` MUST match the owning user of `donor_report_id` (enforced in service layer).
- Cascade delete when report is deleted.

---

### 2.2 Object Storage

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `storage_ref` | `storage_ref` | TEXT | NO | — | S3-compatible key in Railway Buckets; scoped per user |
| `original_filename` | `original_filename` | TEXT | NO | — | Client-provided filename |
| `mime_type` | `mime_type` | TEXT | NO | — | e.g. `application/pdf` |
| `size_bytes` | `size_bytes` | BIGINT | NO | — | MUST be > 0 |

**Rules**
- `storage_ref` is opaque to clients; never returned for direct public URL access.
- Upload/download flows go through authenticated API only.

---

### 2.3 Classification & Extraction

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `classification` | `classification` | TEXT | YES | NULL | CHECK — ENUM_REGISTRY §5.3; set after classifier runs |
| `extracted_json` | `extracted_json` | JSONB | NO | `'{}'::jsonb` | Per-document extraction output |
| `extraction_status` | `extraction_status` | TEXT | NO | `'PENDING'` | CHECK — ENUM_REGISTRY §5.4 |

**Allowed `classification` values (nullable until classified):**  
`proposal` | `grant_letter` | `mou` | `indicator_data` | `photo` | `deck` | `other`

**Allowed `extraction_status` values:**  
`PENDING` | `PROCESSING` | `COMPLETE` | `FAILED`

---

### 2.4 `extracted_json` shape (contract summary)

```json
{
  "extractor_agent": "string",
  "extracted_at": "ISO-8601 or null",
  "raw_text_ref": "string or null",
  "structured": {},
  "confidence": "number 0-1 or null",
  "error": "string or null"
}
```

`structured` payload varies by `classification`; reconciler merges into `donor_reports.knowledge_bank_json`.

---

### 2.5 Timestamps

| DB column | Python attribute | Type | Null | Default | Constraints |
|-----------|------------------|------|------|---------|-------------|
| `created_at` | `created_at` | TIMESTAMPTZ | NO | `now()` | — |

**Note:** No `updated_at` on this table (per locked data model).

---

## 3. Indexes

| Index | Purpose |
|-------|---------|
| `(donor_report_id, created_at)` | List documents for a report |
| `(user_id)` | User-scoped queries |
| `(donor_report_id, classification)` | Route to extractors |

---

## 4. FK Direction Rule

| This table FK | Target | Direction |
|---------------|--------|-----------|
| `donor_report_id` | `donor_reports` | M&E → M&E ✓ |
| `user_id` | `users` | M&E → core ✓ |

**No core table** FKs to `uploaded_documents`.

---

## 5. Relationship to Other Artefacts

- `DB_FIELD_CONTRACT_DONOR_REPORTS.md`
- `DB_FIELD_CONTRACT_REPORT_JOBS.md`
- `API_CONTRACT.md` §12.3 — upload endpoint
- `ENUM_REGISTRY.md` §5.3, §5.4

---

## 6. Build Enforcement

- Quota/entitlement for uploads gated to `IMPACT_PRO` (Stage J); contract allows upload API shape in §12 regardless.
- `extracted_json` uses `_json` suffix; no alias.
