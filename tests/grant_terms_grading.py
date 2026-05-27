"""Shared graders for D3 grant-terms extractor tests and live gate."""

from __future__ import annotations

import json
from typing import Any

from app.reports.schemas.grant_terms_extraction_v1 import (
    DateRangeTerms,
    GrantTermsExtractionOutput,
)


def _collect_reporting_period_raws(reporting_period: DateRangeTerms | dict) -> list[str]:
    if isinstance(reporting_period, dict):
        raws: list[str] = []
        for side in ("start", "end"):
            field = reporting_period.get(side) or {}
            if field.get("multi_value"):
                for sv in field.get("stated_values") or []:
                    if sv.get("raw"):
                        raws.append(sv["raw"])
            elif field.get("raw"):
                raws.append(field["raw"])
        return raws

    raws = []
    for field in (reporting_period.start, reporting_period.end):
        if field.multi_value:
            raws.extend(sv.raw for sv in field.stated_values if sv.raw)
        elif field.raw:
            raws.append(field.raw)
    return raws


def assert_reporting_period_conflict_intact(
    reporting_period: DateRangeTerms | dict,
    planted: dict,
) -> None:
    """Both intra-doc framings must survive; reconciliation is E1's job."""
    assert planted.get("expect_multi_value") is True

    if isinstance(reporting_period, dict):
        start = reporting_period.get("start") or {}
        end = reporting_period.get("end") or {}
        multi = bool(start.get("multi_value") or end.get("multi_value"))
        stated_count = len(start.get("stated_values") or []) + len(
            end.get("stated_values") or []
        )
    else:
        start = reporting_period.start
        end = reporting_period.end
        multi = start.multi_value or end.multi_value
        stated_count = len(start.stated_values) + len(end.stated_values)

    assert multi, "reporting_period conflict requires multi_value on start or end"
    assert stated_count >= 2, "conflict requires at least two stated values"

    raws = _collect_reporting_period_raws(reporting_period)
    combined = " ".join(raws).lower()

    contractual_start = "15 october 2024" in combined
    contractual_end = "14 october 2025" in combined
    assert contractual_start and contractual_end, (
        "contractual framing must include 15 October 2024 and 14 October 2025"
    )

    whole_alt = "october to september" in combined
    split_alt = "october" in combined and "september" in combined
    assert whole_alt or split_alt, (
        "inception framing must be 'October to September' or October+September split"
    )


def _field_raw(field: Any) -> str:
    if isinstance(field, dict):
        if field.get("absent"):
            return ""
        if field.get("multi_value"):
            return " ".join(
                (sv.get("raw") or "") for sv in field.get("stated_values") or []
            )
        return field.get("raw") or ""
    if field.absent:
        return ""
    if field.multi_value:
        return " ".join(sv.raw or "" for sv in field.stated_values)
    return field.raw or ""


def _term_field_canonical(field: Any) -> dict:
    if isinstance(field, dict):
        return {
            "absent": field.get("absent", False),
            "raw": field.get("raw"),
            "normalized": field.get("normalized"),
            "multi_value": field.get("multi_value", False),
            "stated_values": sorted(
                [
                    {
                        "raw": sv.get("raw"),
                        "normalized": sv.get("normalized"),
                    }
                    for sv in field.get("stated_values") or []
                ],
                key=lambda x: (x.get("raw") or "", x.get("normalized") or ""),
            ),
        }
    return {
        "absent": field.absent,
        "raw": field.raw,
        "normalized": field.normalized,
        "multi_value": field.multi_value,
        "stated_values": sorted(
            [
                {"raw": sv.raw, "normalized": sv.normalized}
                for sv in field.stated_values
            ],
            key=lambda x: (x["raw"] or "", x["normalized"] or ""),
        ),
    }


def _reporting_period_stability_key(reporting_period: DateRangeTerms | dict) -> dict:
    """Conflict-preserving slice — allows inception raw phrasing variance."""
    raws = _collect_reporting_period_raws(reporting_period)
    combined = " ".join(raws).lower()
    norms: set[str] = set()
    if isinstance(reporting_period, dict):
        for side in ("start", "end"):
            field = reporting_period.get(side) or {}
            if field.get("normalized"):
                norms.add(field["normalized"])
            for sv in field.get("stated_values") or []:
                if sv.get("normalized"):
                    norms.add(sv["normalized"])
    else:
        for field in (reporting_period.start, reporting_period.end):
            if field.normalized:
                norms.add(field.normalized)
            for sv in field.stated_values:
                if sv.normalized:
                    norms.add(sv.normalized)
    if isinstance(reporting_period, dict):
        multi = bool(
            (reporting_period.get("start") or {}).get("multi_value")
            or (reporting_period.get("end") or {}).get("multi_value")
        )
    else:
        multi = reporting_period.start.multi_value or reporting_period.end.multi_value

    return {
        "contractual_norms": sorted(
            n for n in norms if n in {"2024-10-15", "2025-10-14"}
        ),
        "has_october": "october" in combined,
        "has_september": "september" in combined,
        "multi_value": multi,
    }


def stability_fingerprint(structured: GrantTermsExtractionOutput | dict) -> str:
    """Locked contract fields for gate stability — excludes non-deterministic obligation excerpts."""
    if isinstance(structured, GrantTermsExtractionOutput):
        data = structured.model_dump(mode="json")
    else:
        data = structured

    amt = data["award_budget"]["amount"]
    amt_norm = (amt.get("normalized") or "").replace(",", "")
    deadlines = [
        (d.get("normalized") or "") for d in data.get("reporting_deadlines") or []
    ]
    # AR pack due date is load-bearing; signing deadline is optional in the letter.
    annual_review_deadline = "2025-11-21" if "2025-11-21" in deadlines else None

    canonical = {
        "funder_normalized": data["funder"].get("normalized"),
        "grant_reference_normalized": data["grant_reference"].get("normalized"),
        "award_budget_amount_normalized": amt_norm,
        "award_budget_currency_normalized": data["award_budget"]["currency"].get(
            "normalized"
        ),
        "grant_period_start_normalized": data["grant_period"]["start"].get("normalized"),
        "grant_period_end_normalized": data["grant_period"]["end"].get("normalized"),
        "reporting_period": _reporting_period_stability_key(data["reporting_period"]),
        "annual_review_deadline_normalized": annual_review_deadline,
    }
    return json.dumps(canonical, sort_keys=True)


def content_fingerprint(structured: GrantTermsExtractionOutput | dict) -> str:
    """Full contract-field fingerprint — excludes confidence, latency, tokens."""
    if isinstance(structured, GrantTermsExtractionOutput):
        data = structured.model_dump(mode="json")
    else:
        data = structured

    obligations = sorted(
        [
            {
                "report_type": o.get("report_type"),
                "frequency": o.get("frequency"),
                "raw": o.get("raw"),
            }
            for o in data.get("reporting_obligations") or []
        ],
        key=lambda x: (x["report_type"], x["raw"]),
    )
    deadlines = sorted(
        [_term_field_canonical(d) for d in data.get("reporting_deadlines") or []],
        key=lambda x: json.dumps(x, sort_keys=True),
    )

    canonical = {
        "funder": _term_field_canonical(data["funder"]),
        "grant_reference": _term_field_canonical(data["grant_reference"]),
        "award_budget": {
            "amount": _term_field_canonical(data["award_budget"]["amount"]),
            "currency": _term_field_canonical(data["award_budget"]["currency"]),
            "tranches": sorted(
                [
                    {
                        "raw": t.get("raw"),
                        "normalized": t.get("normalized"),
                    }
                    for t in data["award_budget"].get("tranches") or []
                ],
                key=lambda x: x.get("raw") or "",
            ),
        },
        "grant_period": {
            "start": _term_field_canonical(data["grant_period"]["start"]),
            "end": _term_field_canonical(data["grant_period"]["end"]),
        },
        "reporting_period": {
            "start": _term_field_canonical(data["reporting_period"]["start"]),
            "end": _term_field_canonical(data["reporting_period"]["end"]),
        },
        "reporting_obligations": obligations,
        "reporting_deadlines": deadlines,
    }
    return json.dumps(canonical, sort_keys=True)


def assert_answer_key_present(structured: GrantTermsExtractionOutput, key: dict) -> None:
    exp = key["expected_present"]

    for sub in exp["funder"]["raw_substrings"]:
        assert sub.lower() in _field_raw(structured.funder).lower()
    assert not structured.funder.absent

    assert structured.grant_reference.normalized == exp["grant_reference"]["normalized"]

    amt = structured.award_budget.amount
    for sub in exp["award_budget"]["amount"]["raw_substrings"]:
        assert sub in (amt.raw or "")
    assert amt.normalized == exp["award_budget"]["amount"]["normalized"]
    assert (
        structured.award_budget.currency.normalized
        == exp["award_budget"]["currency"]["normalized"]
    )
    assert len(structured.award_budget.tranches) == 0

    assert (
        structured.grant_period.start.normalized
        == exp["grant_period"]["start"]["normalized"]
    )
    assert (
        structured.grant_period.end.normalized == exp["grant_period"]["end"]["normalized"]
    )

    assert len(structured.reporting_obligations) >= exp["reporting_obligations_min"]
    assert any(
        o.report_type.lower().find(t) >= 0 or (o.raw or "").lower().find(t) >= 0
        for o in structured.reporting_obligations
        for t in exp["reporting_obligation_types"]
    )

    assert len(structured.reporting_deadlines) >= 1
    assert (
        structured.reporting_deadlines[0].normalized
        == exp["reporting_deadlines"][0]["normalized"]
    )


def assert_no_budget_drift(structured: GrantTermsExtractionOutput, key: dict) -> None:
    guard = key["planted_conflicts"]["conflict_budget_cross_doc_note"]
    amt = structured.award_budget.amount
    for sub in guard["expected_raw_substrings"]:
        assert sub in (amt.raw or "")
    norm = (amt.normalized or "").replace(",", "")
    for forbidden in guard["forbidden_normalized_amounts"]:
        assert forbidden.replace(",", "") not in norm


def grade_extraction_output(
    structured: GrantTermsExtractionOutput,
    key: dict,
) -> None:
    """Full answer-key grading for correctness gate run."""
    assert structured.extraction_outcome == "complete"
    assert_answer_key_present(structured, key)
    assert_no_budget_drift(structured, key)
    planted = key["planted_conflicts"]["conflict_3_reporting_period_intra_doc"]
    assert_reporting_period_conflict_intact(structured.reporting_period, planted)
