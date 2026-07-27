"""Layer 5 — eighteen named forbidden-output assertions."""

from __future__ import annotations

import re
from typing import Any

from app.reports.eval.bundle_schema import ScoreableBundle
from app.reports.eval.golden_pack import GoldenPack
from app.reports.eval.starvation import is_starved
from app.reports.eval.verdicts import AssertionClass, AssertionResult, Verdict

# Deterministic fingerprints for named instances (floor for dual / deterministic).
_DETERMINISTIC_PATTERNS: dict[str, list[re.Pattern[str]]] = {
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


def _corpus(bundle: ScoreableBundle) -> str:
    parts = [bundle.export_text or ""]
    content = bundle.content_json or {}
    parts.append(str(content))
    ga = bundle.gap_analysis or {}
    parts.append(str(ga))
    return "\n".join(parts)


def _questions_corpus(bundle: ScoreableBundle) -> str:
    ga = bundle.gap_analysis or {}
    return str(ga).lower()


def evaluate_layer5(bundle: ScoreableBundle, pack: GoldenPack) -> list[AssertionResult]:
    results: list[AssertionResult] = []
    corpus = _corpus(bundle)
    qcorpus = _questions_corpus(bundle)

    for fb in pack.forbidden:
        fid = fb["id"]
        method = fb.get("detection_method") or "judged"
        severity = fb.get("severity") or ""
        name = f"{fid}: {(fb.get('forbidden_output') or '')[:72]}"

        # Choose starvation family
        if fid in {"FB-14", "FB-15"}:
            family = "l5_forbidden_gaps"
        else:
            family = "l5_forbidden_content"

        if is_starved(bundle, family):
            results.append(
                AssertionResult(
                    assertion_id=fid,
                    layer=5,
                    name=name,
                    assertion_class=AssertionClass.INVARIANT,
                    verdict=Verdict.PASS_BY_STARVATION,
                    detail=f"Upstream stage absent for {family}",
                    metrics={"severity": severity, "detection_method": method},
                )
            )
            continue

        det_hit = False
        for pat in _DETERMINISTIC_PATTERNS.get(fid, []):
            target = qcorpus if fid in {"FB-14", "FB-15"} else corpus
            if pat.search(target):
                det_hit = True
                break

        # FB-05 special: deterministic arm = indicator mentioned at all in content?
        # Absence of OP2.3/OP4.2 without disclosure is the failure mode.
        if fid == "FB-05":
            mentions_op23 = bool(re.search(r"op2\.?3|op2_3|safeguarding referral", corpus, re.I))
            mentions_op42 = bool(re.search(r"op4\.?2|op4_2|learning brief", corpus, re.I))
            disclosed = bool(
                re.search(r"unreported|not reported|reporting gap|absent from", corpus, re.I)
            )
            # Deterministic floor: if neither indicator string appears, treat as omission candidate
            det_omission = not (mentions_op23 and mentions_op42)
            if method == "dual":
                if det_omission and not disclosed:
                    # Judged arm required for "without flagging" — surface REVIEW-REQUIRED
                    # when deterministic sees omission and no disclosure phrase.
                    results.append(
                        AssertionResult(
                            assertion_id=fid,
                            layer=5,
                            name=name,
                            assertion_class=AssertionClass.INVARIANT,
                            verdict=Verdict.REVIEW_REQUIRED,
                            detail=(
                                "Deterministic arm: one or both of OP2.3/OP4.2 absent from corpus; "
                                "no disclosure phrase found — judged arm must confirm silent impoverishment"
                            ),
                            metrics={
                                "severity": severity,
                                "detection_method": method,
                                "deterministic_arm": "omission_candidate",
                                "judged_arm": "REVIEW-REQUIRED",
                            },
                        )
                    )
                    continue
                if det_omission and disclosed:
                    results.append(
                        AssertionResult(
                            assertion_id=fid,
                            layer=5,
                            name=name,
                            assertion_class=AssertionClass.INVARIANT,
                            verdict=Verdict.PASS,
                            detail="Indicators unreported but disclosure phrase present",
                            metrics={"severity": severity, "detection_method": method},
                        )
                    )
                    continue

        if method == "deterministic":
            results.append(
                AssertionResult(
                    assertion_id=fid,
                    layer=5,
                    name=name,
                    assertion_class=AssertionClass.INVARIANT,
                    verdict=Verdict.FAIL if det_hit else Verdict.PASS,
                    detail="Deterministic fingerprint hit" if det_hit else "No deterministic hit",
                    metrics={"severity": severity, "detection_method": method, "deterministic_hit": det_hit},
                )
            )
        elif method == "judged":
            # Never auto-PASS / auto-FAIL from an uncalibrated judge — REVIEW-REQUIRED if
            # a heuristic fires; otherwise PASS only means "no heuristic trigger".
            # For moat safety: if we cannot run a judge, absence of heuristic ≠ demonstrated safety.
            # Heuristic: look for strong keywords from forbidden text.
            keywords = re.findall(r"[A-Za-z]{5,}", fb.get("forbidden_output") or "")
            heuristic = sum(1 for k in keywords[:8] if k.lower() in corpus.lower()) >= 3
            results.append(
                AssertionResult(
                    assertion_id=fid,
                    layer=5,
                    name=name,
                    assertion_class=AssertionClass.INVARIANT,
                    verdict=Verdict.REVIEW_REQUIRED if heuristic else Verdict.PASS,
                    detail=(
                        "Judged forbidden — heuristic trigger; REVIEW-REQUIRED (never auto-PASS a moat failure)"
                        if heuristic
                        else "Judged forbidden — no heuristic trigger (uncalibrated; not a demonstrated clear)"
                    ),
                    metrics={
                        "severity": severity,
                        "detection_method": method,
                        "heuristic_trigger": heuristic,
                    },
                )
            )
        else:  # dual
            if det_hit:
                results.append(
                    AssertionResult(
                        assertion_id=fid,
                        layer=5,
                        name=name,
                        assertion_class=AssertionClass.INVARIANT,
                        verdict=Verdict.FAIL,
                        detail="Dual: deterministic arm fired on named instance",
                        metrics={
                            "severity": severity,
                            "detection_method": method,
                            "deterministic_arm": "FAIL",
                        },
                    )
                )
            else:
                # Judged arm for general class — REVIEW-REQUIRED if soft heuristic fires
                keywords = re.findall(r"[A-Za-z]{5,}", fb.get("forbidden_output") or "")
                heuristic = sum(1 for k in keywords[:6] if k.lower() in corpus.lower()) >= 4
                results.append(
                    AssertionResult(
                        assertion_id=fid,
                        layer=5,
                        name=name,
                        assertion_class=AssertionClass.INVARIANT,
                        verdict=Verdict.REVIEW_REQUIRED if heuristic else Verdict.PASS,
                        detail=(
                            "Dual: judged arm REVIEW-REQUIRED for general class"
                            if heuristic
                            else "Dual: deterministic arm clear; judged arm no heuristic trigger"
                        ),
                        metrics={
                            "severity": severity,
                            "detection_method": method,
                            "deterministic_arm": "clear",
                            "judged_arm": "REVIEW-REQUIRED" if heuristic else "clear",
                        },
                    )
                )

    return results
