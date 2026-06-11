"""§12.6 GET gap-check and §12.7 PATCH gap-answers for Gate 2 UI."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.reports.schemas.gap_check import GapAnswerPatchInput, GapCheckMissingItemResponse
from app.reports.schemas.gate2_gap_answers import Gate2GapResponseInput
from app.reports.services.gate2_gap_answer_service import (
    _persisted_answer,
    _remaining_gaps,
    re_enqueue_gate2_job,
)
from app.reports.services.gate_preconditions import (
    require_gap_analysis,
    require_gate1_confirmed,
)
from app.reports.services.report_access import get_owned_donor_report


def _confirm_existing_excerpt(
    gap: dict[str, Any],
    facts: dict[str, Any],
) -> str | None:
    if gap.get("suggested_action") != "confirm_existing":
        return None
    ref = str(gap.get("required_item_ref") or "")
    ref_token = ref.replace("_", "").lower()
    for fact_key, fact in facts.items():
        if not isinstance(fact, dict):
            continue
        key_lower = str(fact_key).lower()
        if ref_token and ref_token in key_lower.replace("_", ""):
            excerpt = (fact.get("provenance") or {}).get("excerpt") or fact.get("value")
            if excerpt:
                return str(excerpt)[:500]
    return None


def _readiness_message(readiness_basis: str | None, unanswered: int) -> str:
    if readiness_basis == "post_draft":
        if unanswered == 0:
            return "Your draft is ready to finalize."
        if unanswered == 1:
            return "1 item needs your input before we finalize the draft."
        return f"{unanswered} items need your input before we finalize the draft."
    if unanswered == 0:
        return "All required data items are on file."
    if unanswered == 1:
        return "1 item needs your input before we can draft your report."
    return f"{unanswered} items need your input before we can draft your report."


def _missing_item_from_gap(
    gap: dict[str, Any],
    *,
    facts: dict[str, Any] | None = None,
) -> GapCheckMissingItemResponse:
    section_label = str(gap.get("section_label") or gap.get("section_key") or "")
    question = str(gap.get("question") or "")
    return GapCheckMissingItemResponse(
        item_key=str(gap["item_key"]),
        label=section_label or str(gap.get("required_item_ref") or gap["item_key"]),
        prompt=question,
        severity=gap.get("severity") or "required",
        section_key=gap.get("section_key"),
        section_label=gap.get("section_label"),
        question=gap.get("question"),
        rationale=gap.get("rationale"),
        owner=gap.get("owner"),
        requirement_type=gap.get("requirement_type"),
        suggested_action=gap.get("suggested_action"),
        confirm_existing_excerpt=_confirm_existing_excerpt(gap, facts or {}),
    )


def get_gap_check(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    require_gate1_confirmed(report.knowledge_bank_json)
    surfaced = require_gap_analysis(report.gap_analysis_json)
    kb = report.knowledge_bank_json or {}
    facts = kb.get("facts") or {}
    gap_answers = kb.get("gap_answers") or {}
    remaining = _remaining_gaps(surfaced, gap_answers)
    ga = report.gap_analysis_json or {}
    readiness_basis = ga.get("readiness_basis")
    return {
        "donor_report_id": donor_report_id,
        "open_items_count": len(remaining),
        "ready_for_gate2": bool(ga.get("ready_for_gate2")),
        "missing_items": [
            _missing_item_from_gap(gap, facts=facts).model_dump() for gap in remaining
        ],
        "gate2_confirmed_at": kb.get("gate2_confirmed_at"),
        "readiness_basis": readiness_basis,
        "readiness_message": _readiness_message(readiness_basis, len(remaining)),
    }


def _patch_input_to_gate2(entry: GapAnswerPatchInput) -> Gate2GapResponseInput:
    disposition = entry.disposition or "answered"
    if disposition == "skipped":
        return Gate2GapResponseInput(
            disposition="skipped",
            skip_reason=entry.skip_reason or "cannot_provide",
            answer_text=None,
        )
    return Gate2GapResponseInput(
        disposition="answered",
        answer_text=entry.answer_text or "",
        skip_reason=None,
    )


def patch_gap_answers(
    db: Session,
    *,
    donor_report_id: uuid.UUID,
    user_id: uuid.UUID,
    gap_answers_patch: dict[str, GapAnswerPatchInput],
    confirm_gate2: bool = False,
) -> dict[str, Any]:
    report = get_owned_donor_report(
        db, donor_report_id=donor_report_id, user_id=user_id
    )
    require_gate1_confirmed(report.knowledge_bank_json)
    surfaced = require_gap_analysis(report.gap_analysis_json)
    surfaced_keys = {str(g["item_key"]) for g in surfaced if g.get("item_key")}

    unknown = sorted(set(gap_answers_patch) - surfaced_keys)
    if unknown:
        raise DomainError(
            error_code="GATE2_UNKNOWN_GAP_KEYS",
            message="One or more gap answers reference gaps not surfaced by E3",
            status_code=422,
            details={"unknown_item_keys": unknown},
        )

    kb = dict(report.knowledge_bank_json or {})
    gap_answers = dict(kb.get("gap_answers") or {})
    now = datetime.now(timezone.utc)

    for item_key, entry in gap_answers_patch.items():
        gate2_input = _patch_input_to_gate2(entry)
        gap_answers[item_key] = _persisted_answer(gate2_input, responded_at=now)

    kb["gap_answers"] = gap_answers
    kb.pop("gate2_confirmed_at", None)
    report.knowledge_bank_json = kb
    db.add(report)

    remaining = _remaining_gaps(surfaced, gap_answers)
    if confirm_gate2:
        if remaining:
            raise DomainError(
                error_code="GATE2_INCOMPLETE",
                message="All surfaced gaps must be answered or skipped before confirming Gate 2",
                status_code=409,
                details={"remaining_count": len(remaining)},
            )
        kb["gate2_confirmed_at"] = now.isoformat()
        report.knowledge_bank_json = kb
        db.add(report)
        re_enqueue_gate2_job(db, donor_report_id=donor_report_id)

    db.commit()
    db.refresh(report)
    return get_gap_check(db, donor_report_id=donor_report_id, user_id=user_id)
