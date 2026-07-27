"""Load and verify the FCDO BridgeLight AR1 golden pack fixtures."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PACK_DIR = (
    REPO_ROOT / "tests" / "fixtures" / "golden" / "fcdo_bridgelight_ar1_v1"
)


def _sha256_canonical(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GoldenPack:
    pack_dir: Path
    manifest: dict[str, Any]
    facts: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    gaps: dict[str, Any]
    forbidden: list[dict[str, Any]]
    report_reference: dict[str, Any]

    @property
    def dataset_version(self) -> str:
        return str(self.manifest["dataset_version"])

    @property
    def content_checksum(self) -> str:
        return str(self.manifest["content_checksum"])

    @property
    def report_markdown(self) -> str:
        """Layer 4 text — always from the fixture file, never inlined elsewhere."""
        return str(self.report_reference["full_markdown"])


def compute_pack_checksum(
    *,
    facts: list[dict[str, Any]],
    conflicts: list[dict[str, Any]],
    gaps: dict[str, Any],
    forbidden: list[dict[str, Any]],
    report_reference: dict[str, Any],
) -> str:
    payload = {
        "facts": facts,
        "conflicts": conflicts,
        "gaps": {k: gaps[k] for k in ("clusters", "counter_list", "target_note")},
        "forbidden": forbidden,
        "report_reference": {
            "prose_uncalibrated": report_reference["prose_uncalibrated"],
            "full_markdown_sha256": hashlib.sha256(
                report_reference["full_markdown"].encode("utf-8")
            ).hexdigest(),
            "sections_present": report_reference["sections_present"],
        },
    }
    return _sha256_canonical(payload)


def load_golden_pack(pack_dir: Path | None = None, *, verify_checksum: bool = True) -> GoldenPack:
    root = Path(pack_dir) if pack_dir else DEFAULT_PACK_DIR
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    facts = json.loads((root / "facts.json").read_text(encoding="utf-8"))
    conflicts = json.loads((root / "conflicts.json").read_text(encoding="utf-8"))
    gaps = json.loads((root / "gaps.json").read_text(encoding="utf-8"))
    forbidden = json.loads((root / "forbidden.json").read_text(encoding="utf-8"))
    report_reference = json.loads(
        (root / "report_reference.json").read_text(encoding="utf-8")
    )
    if verify_checksum:
        actual = compute_pack_checksum(
            facts=facts,
            conflicts=conflicts,
            gaps=gaps,
            forbidden=forbidden,
            report_reference=report_reference,
        )
        expected = manifest["content_checksum"]
        if actual != expected:
            raise ValueError(
                f"Golden pack checksum mismatch: expected {expected}, got {actual}"
            )
    return GoldenPack(
        pack_dir=root,
        manifest=manifest,
        facts=facts,
        conflicts=conflicts,
        gaps=gaps,
        forbidden=forbidden,
        report_reference=report_reference,
    )
