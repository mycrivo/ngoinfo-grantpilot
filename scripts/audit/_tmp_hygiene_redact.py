"""Redact real-owner email from artefacts/scripts before hygiene commit."""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REAL = "pranabksingh@gmail.com"
REDACTED = "REDACTED_OWNER@example.invalid"

TARGETS = [
    ROOT / "scripts/_purge_user_account.py",
    ROOT / "scripts/_retry_export.py",
    ROOT / "scripts/_check_user_quota.py",
    ROOT / "docs/artefacts/me_module/audits/snapshots/user_purge_pranabksingh_20260705T160815Z.json",
    ROOT / "docs/artefacts/me_module/audits/snapshots/user_purge_pranabksingh_20260705T185158Z.json",
]

RENAMES = {
    ROOT
    / "docs/artefacts/me_module/audits/snapshots/user_purge_pranabksingh_20260705T160815Z.json": ROOT
    / "docs/artefacts/me_module/audits/snapshots/user_purge_owner_20260705T160815Z.json",
    ROOT
    / "docs/artefacts/me_module/audits/snapshots/user_purge_pranabksingh_20260705T185158Z.json": ROOT
    / "docs/artefacts/me_module/audits/snapshots/user_purge_owner_20260705T185158Z.json",
}


def main() -> None:
    for path in TARGETS:
        if not path.exists():
            print("MISS", path)
            continue
        text = path.read_text(encoding="utf-8")
        if REAL not in text:
            print("NO_HIT", path)
            continue
        path.write_text(text.replace(REAL, REDACTED), encoding="utf-8")
        print("REDACTED", path)

    for src, dst in RENAMES.items():
        if src.exists():
            shutil.move(str(src), str(dst))
            print("RENAMED", src.name, "->", dst.name)

    # Move root FCDO walk logs into audits/
    audits = ROOT / "docs/artefacts/me_module/audits"
    for name in ("FCDO_LIVE_WALK_pranab_20260705.log", "FCDO_LIVE_WALK_pranab_v2.log"):
        src = ROOT / name
        if src.exists():
            dst = audits / name.replace("pranab_", "")
            shutil.move(str(src), str(dst))
            print("MOVED", name, "->", dst.relative_to(ROOT))


if __name__ == "__main__":
    main()
