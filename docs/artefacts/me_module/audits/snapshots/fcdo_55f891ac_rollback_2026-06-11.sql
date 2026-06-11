-- Rollback: restore prod FCDO template from B1 snapshot (2026-06-11)
-- Checksum SHA256: aa6c99264aef29c78039f38891787212063f67dfe9e45a536e4c71dba0b3f4f0
BEGIN;
UPDATE funder_report_templates
SET
  report_sections_json = :report_sections_json::jsonb,
  format_rules_json = :format_rules_json::jsonb,
  terminology_map_json = :terminology_map_json::jsonb,
  version = 1,
  updated_at = now()
WHERE id = '55f891ac-bb8b-4137-bc42-6de8ff935064';
-- Verify affected rows = 1 before COMMIT;
COMMIT;
