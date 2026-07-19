from pathlib import Path

term = Path(
    r"C:\Users\prana\.cursor\projects\c-Users-prana-OneDrive-Desktop-NGOInfo-Grantpilot\terminals\550976.txt"
)
log = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_WITNESSED_WALK_2026-07-19.log")
if term.exists():
    lines = term.read_text(encoding="utf-8", errors="replace").splitlines()
    print("=== TERMINAL header/footer ===")
    print("\n".join(lines[:12]))
    print("...")
    print("\n".join(lines[-30:]))
else:
    print("NO_TERMINAL")
print("=== LOG tail ===")
if log.exists():
    print("\n".join(log.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]))
