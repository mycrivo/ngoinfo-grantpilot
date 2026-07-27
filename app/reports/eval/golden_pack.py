"""Load and verify the FCDO BridgeLight AR1 golden pack fixtures."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PACK_DIR = (
    REPO_ROOT / "tests" / "fixtures" / "golden" / "fcdo_bridgelight_ar1_v1"
)

# Deterministic fingerprints — kept in sync with layers.l5_assertions._DETERMINISTIC_PATTERNS.
# Standing self-check: reference text vs pack's own forbidden patterns.
# D-080: arm is uncalibrated; patterns must not be edited in builder packages.
_DET_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "FB-01": [
        re.compile(r"1[, ]?944"),
        re.compile(r"2[, ]?376"),
        re.compile(r"total row", re.I),
    ],
    "FB-02": [
        re.compile(r"472\s*/\s*684"),
        re.compile(r"ocm1\s*=\s*69", re.I),
    ],
    "FB-04": [re.compile(r"1[, ]?184[, ]?000")],
    "FB-05": [
        re.compile(r"op2\.?3|op2_3", re.I),
        re.compile(r"op4\.?2|op4_2", re.I),
    ],
    "FB-06": [
        re.compile(r"392.*male", re.I),
        re.compile(r"all\s+392.*male", re.I),
    ],
    "FB-09": [re.compile(r"aggregat\w+.*output.?score|output.?score.*aggregat", re.I)],
    "FB-13": [re.compile(r"life[- ]of[- ]programme|burn\s*rate|remaining budget", re.I)],
    "FB-14": [
        re.compile(r"previous recommendations", re.I),
        re.compile(r"impact weightings", re.I),
    ],
    "FB-15": [
        re.compile(r"devtracker", re.I),
        re.compile(r"vfm scoring rubric", re.I),
    ],
    "FB-18": [
        re.compile(r"equity share|%\s+of\s+(beneficiar|girls).*(disabled|ultra-poor)", re.I),
    ],
}


def _sha256_canonical(obj: Any) -> str:
    canonical = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class GoldenPack:
    pack_dir: Path
    manifest: dict[str, Any]
    facts: list[dict[str, Any]]
    conflicts: list[dict[str, Any]]
    gaps: dict[str, Any]
    forbidden: list[dict[str, Any]]
    report_reference: dict[str, Any]
    l5_reference_self_hits: tuple[str, ...] = field(default_factory=tuple)

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

    @property
    def judge_calibrated(self) -> bool:
        # Fail-closed: absent → not calibrated → prose stays advisory.
        return bool(self.report_reference.get("judge_calibrated", False))

    @property
    def reference_prose_conforms_to_v4(self) -> bool:
        return bool(self.report_reference.get("reference_prose_conforms_to_v4", False))


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
            "reference_prose_conforms_to_v4": report_reference["reference_prose_conforms_to_v4"],
            "judge_calibrated": report_reference["judge_calibrated"],
            "full_markdown_sha256": _sha256_text(report_reference["full_markdown"]),
            "prose_rubric_reference_sha256": _sha256_text(
                report_reference.get("prose_rubric_reference") or ""
            ),
            "sections_present": report_reference["sections_present"],
        },
    }
    return _sha256_canonical(payload)


def scan_reference_against_forbidden(full_markdown: str) -> list[str]:
    """Standing pack check: deterministic forbidden patterns vs Layer 4 reference text.

    D-080: observations are recorded; fail-on-load is suspended while the arm is
    uncalibrated. Do not reintroduce an exception list.
    """
    hits: list[str] = []
    for fid, pats in _DET_PATTERNS.items():
        for pat in pats:
            if pat.search(full_markdown):
                hits.append(fid)
                break
    return hits


def load_golden_pack(
    pack_dir: Path | None = None,
    *,
    verify_checksum: bool = True,
    verify_l5_self_check: bool = True,
) -> GoldenPack:
    """Load pack fixtures.

    ``verify_l5_self_check`` controls whether the deterministic self-check *runs*
    (default True). It never fails the load while the L5 deterministic arm is
    uncalibrated (D-080). Reversion: restore fail-on-load only after owner/CTO
    authored and calibrated detectors are recorded in the decision log.
    """
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

    hits: list[str] = []
    if verify_l5_self_check:
        # Record-only while uncalibrated — never raise on observations (D-080).
        hits = scan_reference_against_forbidden(report_reference["full_markdown"])

    return GoldenPack(
        pack_dir=root,
        manifest=manifest,
        facts=facts,
        conflicts=conflicts,
        gaps=gaps,
        forbidden=forbidden,
        report_reference=report_reference,
        l5_reference_self_hits=tuple(hits),
    )
