@echo off
cd /d c:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot
railway logs -s exemplary-encouragement --since 2026-07-19T08:00:00Z > docs\artefacts\me_module\audits\TRACK3_PHASE2_WORKER_LOGS_WINDOW_2026-07-19.txt 2>&1
findstr /i /c:"AUTH_REFRESH_DIAG" /c:"401" docs\artefacts\me_module\audits\TRACK3_PHASE2_WORKER_LOGS_WINDOW_2026-07-19.txt > docs\artefacts\me_module\audits\TRACK3_PHASE2_AUTH_DIAG_RAW_2026-07-19.txt
echo LOG_BYTES=
for %%A in (docs\artefacts\me_module\audits\TRACK3_PHASE2_WORKER_LOGS_WINDOW_2026-07-19.txt) do echo %%~zA
echo AUTH_BYTES=
for %%A in (docs\artefacts\me_module\audits\TRACK3_PHASE2_AUTH_DIAG_RAW_2026-07-19.txt) do echo %%~zA
