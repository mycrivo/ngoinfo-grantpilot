from pathlib import Path

log = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_WITNESSED_WALK_2026-07-19.log")
lines = [ln for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if "AUTH_REFRESH_DIAG" in ln]
out = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_AUTH_REFRESH_DIAG_2026-07-19.txt")
out.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
print("AUTH_REFRESH_DIAG_COUNT=", len(lines))
for ln in lines:
    print(ln[:500])
