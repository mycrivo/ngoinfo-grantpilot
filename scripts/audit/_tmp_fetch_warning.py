import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# railway logs may stream — use --lines if available
try:
    raw = subprocess.check_output(
        [
            "cmd",
            "/c",
            "railway logs --service exemplary-encouragement --lines 200",
        ],
        cwd=str(REPO),
        text=True,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
except subprocess.CalledProcessError as e:
    raw = e.output or str(e)
except Exception as e:
    raw = str(e)

out = Path("docs/artefacts/me_module/audits/TRACK3_PHASE2_WORKER_LOG_SNIPPET_2026-07-19.txt")
out.write_text(raw, encoding="utf-8")
hits = [ln for ln in raw.splitlines() if "FAULT INJECTION" in ln or "fault_injected" in ln]
print("LOG_BYTES", len(raw.encode("utf-8", errors="replace")))
print("FAULT_WARNING_HITS", len(hits))
for ln in hits[:20]:
    print(ln)
