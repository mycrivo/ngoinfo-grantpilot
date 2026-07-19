"""Repo hygiene verify — presence on origin/main + secret scan on untracked."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

REQUIRED_ON_MAIN = [
    "docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md",
    "docs/artefacts/ENV_VARS_REFERENCE.md",
    "docs/artefacts/me_module/audits/TRACK3_STOP_B_EVIDENCE_PACK_2026-07-18.md",
    "docs/artefacts/me_module/audits/TRACK3_NLCF_LIVE_VS_COMMITTED_DRIFT_2026-07-18.json",
    "docs/artefacts/me_module/audits/snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json",
    "docs/artefacts/me_module/audits/TRACK3_CONFIRMING_WALK_EVIDENCE_20260718T162116Z.json",
    "docs/artefacts/me_module/audits/TRACK3_CONFIRMING_WALK_2026-07-18.log",
    "scripts/audit/_common.py",
    "scripts/audit/full_walk.py",
    "scripts/audit/track3_confirming_walk.py",
]

SECRET_RE = re.compile(
    r"(Bearer\s+[A-Za-z0-9._\-]+|access_token|refresh_token|eyJ[A-Za-z0-9_\-]{20,}|sk-[A-Za-z0-9]{20,}|password\s*[:=])",
    re.I,
)
REAL_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@(?!grantpilot-test\.org)[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def run(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, cwd=ROOT, text=True, errors="replace")


def main() -> None:
    print("=== PRESENCE ON origin/main ===")
    missing = []
    for path in REQUIRED_ON_MAIN:
        try:
            run(["git", "cat-file", "-e", f"origin/main:{path}"])
            print(f"OK  {path}")
        except subprocess.CalledProcessError:
            print(f"MISS {path}")
            missing.append(path)

    log = run(["git", "show", "origin/main:docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md"])
    for needle in ["D-053", "D-054", "D-055", "D-056", "D-057", "O-007", "O-008", "O-009"]:
        # D-057 only on disk until we commit
        in_main = needle in log
        print(f"decision_log origin/main {needle}: {'YES' if in_main else 'NO (pending commit if local)'}")

    env = run(["git", "show", "origin/main:docs/artefacts/ENV_VARS_REFERENCE.md"])
    print(
        "ENV_VARS ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE:",
        "YES" if "ME_PROPOSAL_INDUCE_TIMEOUT_DEGRADE" in env else "NO",
    )

    snap = ROOT / "docs/artefacts/me_module/audits/snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json"
    if snap.exists():
        # SHA was of file content historically; confirm file exists and size
        print(f"snapshot_local_bytes={snap.stat().st_size}")
    try:
        run(["git", "cat-file", "-e", "origin/main:docs/artefacts/me_module/audits/snapshots/nlcf_2d5d75b7_pre_track3_2026-07-18.json"])
        # verify mentioned sha in STOP B pack on main
        stopb = run(
            ["git", "show", "origin/main:docs/artefacts/me_module/audits/TRACK3_STOP_B_EVIDENCE_PACK_2026-07-18.md"]
        )
        print("STOP_B mentions 64e6ebc6:", "64e6ebc6" in stopb)
    except subprocess.CalledProcessError:
        print("snapshot missing on main")

    print("\n=== SECRET SCAN (untracked/modified candidates) ===")
    status = run(["git", "status", "--short"])
    paths = []
    for line in status.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path)

    for path in paths:
        p = ROOT / path
        if not p.is_file():
            continue
        if p.suffix.lower() in {".docx", ".png", ".jpg", ".pdf", ".zip"}:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"READ_FAIL {path}: {e}")
            continue
        secrets = SECRET_RE.findall(text)
        emails = sorted(set(REAL_EMAIL_RE.findall(text)))
        if secrets or emails:
            print(f"FLAG {path}: secret_hits={len(secrets)} real_emails={emails[:10]}")
        else:
            # still note grantpilot-test emails as OK
            test_emails = sorted(set(re.findall(r"[A-Za-z0-9._%+\-]+@grantpilot-test\.org", text)))
            if test_emails:
                print(f"OK   {path}: test_emails={len(test_emails)}")
            else:
                print(f"OK   {path}")

    print("\n=== CATEGORY D (app/tests/alembic/frontend product) ===")
    product = [
        p
        for p in paths
        if p.startswith("app/")
        or p.startswith("tests/")
        or p.startswith("alembic/")
        or p.startswith("ngoinfo-grantpilot-frontend/")
    ]
    print("product_paths=", product or "NONE")
    print("missing_required=", missing or "NONE")


if __name__ == "__main__":
    main()
