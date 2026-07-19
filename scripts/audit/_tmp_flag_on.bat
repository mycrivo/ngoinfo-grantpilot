@echo off
cd /d c:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot
railway variables set ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE=true --service exemplary-encouragement
if errorlevel 1 exit /b 1
railway variables --json --service exemplary-encouragement > .git\rw_worker_vars.json
railway variables --json --service ngoinfo-grantpilot > .git\rw_web_vars.json
python scripts\audit\_tmp_flag_readback.py
