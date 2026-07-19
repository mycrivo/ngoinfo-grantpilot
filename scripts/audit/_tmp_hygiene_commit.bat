@echo off
cd /d c:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot
setlocal EnableExtensions

echo === COMMIT 1 governance ===
git add docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md
git commit -m "docs(me): D-057 Track 3 Phase 2 witnessed-walk decision" -m "Record first prod checkpoint firing, induced report IDs, flag window, auth-diag outcome, and window-exposure statement."
if errorlevel 1 echo COMMIT1_FAILED

echo === COMMIT 2 evidence ===
git add ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_ANSWERED_b007f125.json ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_AUTH_DIAG_RAW_2026-07-19.txt ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_AUTH_REFRESH_DIAG_2026-07-19.txt ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_FAULT_WARNING_CAPTURE_2026-07-19.txt ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_FIRST_PROD_CHECKPOINT_b007f125.json ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_FLAG_WINDOW_2026-07-19.json ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_SKIP_46fdb1b1.json ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_SKIP_COMMUNITY_INSPECT.json ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_STOP3_EVIDENCE_PACK_2026-07-19.md ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_WITNESSED_WALK_2026-07-19.log ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_WORKER_LOGS_WINDOW_2026-07-19.txt ^
  docs/artefacts/me_module/audits/TRACK3_PHASE2_WORKER_LOG_SNIPPET_2026-07-19.txt ^
  docs/artefacts/me_module/audits/TRACK0_D046_PROD_VALIDATION_20260705.md ^
  docs/artefacts/me_module/audits/TRACK0_D046_PROD_VALIDATION_20260705T230457Z.md ^
  docs/artefacts/me_module/audits/FCDO_LIVE_WALK_20260705.log ^
  docs/artefacts/me_module/audits/FCDO_LIVE_WALK_v2.log ^
  docs/artefacts/me_module/audits/snapshots/user_purge_owner_20260705T160815Z.json ^
  docs/artefacts/me_module/audits/snapshots/user_purge_owner_20260705T185158Z.json
git commit -m "docs(me): Track 3 Phase 2 STOP 3 + older audit evidence artefacts" -m "Commit induced-walk evidence packs, flag window, auth-diag capture, Track 0 D046 notes, FCDO walk logs, and redacted owner purge snapshots. Real owner email redacted to REDACTED_OWNER@example.invalid; filenames sanitized."
if errorlevel 1 echo COMMIT2_FAILED

echo === COMMIT 3 tooling ===
git add ^
  scripts/_check_report_status_db.py ^
  scripts/_check_user_quota.py ^
  scripts/_purge_user_account.py ^
  scripts/_resume_full_walk.py ^
  scripts/_retry_export.py ^
  scripts/audit/track0_d046_prod_validation.py ^
  scripts/audit/track3_phase2_witnessed_walk.py ^
  scripts/audit/_tmp_check_job.py ^
  scripts/audit/_tmp_extract_auth_diag.py ^
  scripts/audit/_tmp_fetch_warning.py ^
  scripts/audit/_tmp_flag_off.bat ^
  scripts/audit/_tmp_flag_off_stamp.py ^
  scripts/audit/_tmp_flag_on.bat ^
  scripts/audit/_tmp_flag_readback.py ^
  scripts/audit/_tmp_flag_status.py ^
  scripts/audit/_tmp_hygiene_verify.py ^
  scripts/audit/_tmp_hygiene_redact.py ^
  scripts/audit/_tmp_hygiene_commit.bat ^
  scripts/audit/_tmp_inspect_answered_markers.py ^
  scripts/audit/_tmp_inspect_skip_community.py ^
  scripts/audit/_tmp_pull_auth_diag.bat ^
  scripts/audit/_tmp_resume_answered.py ^
  scripts/audit/_tmp_rw_inspect.py ^
  scripts/audit/_tmp_save_checkpoint.py ^
  scripts/audit/_tmp_sleep.py ^
  scripts/audit/_tmp_stamp_window_start.py ^
  scripts/audit/_tmp_tail_resume.py ^
  scripts/audit/_tmp_tail_walk.py ^
  scripts/audit/_tmp_wait_deploy.py
git commit -m "chore(audit): Phase 2 walk tooling and loose ops scripts" -m "Add track3_phase2_witnessed_walk, Track 0 D046 validator, Railway flag helpers, and older resume/quota/purge helpers. Default owner emails redacted."
if errorlevel 1 echo COMMIT3_FAILED

echo === STATUS ===
git status --short
git log -5 --oneline
endlocal
