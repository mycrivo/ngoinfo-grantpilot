from pathlib import Path
import sys

tid = sys.argv[1] if len(sys.argv) > 1 else "164810"
term = Path(
    rf"C:\Users\prana\.cursor\projects\c-Users-prana-OneDrive-Desktop-NGOInfo-Grantpilot\terminals\{tid}.txt"
)
log = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_WITNESSED_WALK_2026-07-19.log")
if term.exists():
    lines = term.read_text(encoding="utf-8", errors="replace").splitlines()
    print("\n".join(lines[:10]))
    print("...")
    print("\n".join(lines[-40:]))
else:
    print("NO_TERM", tid)
print("---LOG TAIL---")
print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-30:]))
