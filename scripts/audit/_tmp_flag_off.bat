@echo off
cd /d c:\Users\prana\OneDrive\Desktop\NGOInfo-Grantpilot
railway variables delete ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE --service exemplary-encouragement
if errorlevel 1 (
  railway variables set ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE=false --service exemplary-encouragement
)
python scripts\audit\_tmp_flag_off_stamp.py
