"""F1 report section synthesis — persist to donor_reports.content_json."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.integrations.openai_client import OpenAIClient, OpenAIServiceError
from app.reports.ai.prompts.synthesis import (
    REPORT_SYNTHESIS_SYSTEM_PROMPT,
    build_synthesis_user_prompt,
)
from app.reports.models.donor_report import DonorReport
from app.reports.models.enums import DonorReportStatus
from app.reports.models.funder_report_template import FunderReportTemplate
from app.reports.schemas.content_json_v1 import (
    build_failed_section,
    build_generated_section,
    merge_content_json_after_synthesis,
    merge_synthesis_sections,
    section_needs_synthesis,
    sections_by_key,
)
from app.reports.services.gate_preconditions import require_gate2_confirmed
from app.reports.services.report_inputs_builder import build_report_inputs_for_section
from app.reports.services.synthesis_citation_emission import emit_claim_granular_evidence
from app.reports.services.synthesis_output_hygiene import sanitize_generated_content

logger = logging.getLogger("reports.services.report_synthesis")

DEFAULT_SYNTHESIS_MAX_CONCURRENCY = 2
DEFAULT_MAX_TOKENS = 2500
MIN_MAX_TOKENS = 800
SYNTHESIS_TEMPERATURE = 0.65
SYNTHESIS_FREQUENCY_PENALTY = 0.4

QueryFnSynthesis = Callable[[str, str, str], dict[str, Any]]


def get_synthesis_max_concurrency() -> int:
    """Max F1 sections in flight. Env: ME_SYNTHESIS_MAX_CONCURRENCY (default 2)."""
    configured = get_settings().ME_SYNTHESIS_MAX_CONCURRENCY
    return max(1, int(configured))


class ReportSynthesisServiceError(Exception):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ReportSynthesisStageResult:
    section_count: int
    generated: int
    failed: int
    degraded: bool
    warnings: list[str]


def _max_tokens_for_section(word_limit: int | None) -> int:
    if not word_limit or word_limit <= 0:
        return DEFAULT_MAX_TOKENS
    return max(MIN_MAX_TOKENS, min(int(word_limit * 2.5), DEFAULT_MAX_TOKENS))


def _extract_json_payload(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices") or []
    if not choices:
        raise ValueError("OpenAI response missing choices")
    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise ValueError("OpenAI response missing content")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise ValueError("OpenAI response JSON must be an object")
    return parsed


def _call_openai_section(
    *,
    section_key: str,
    system_prompt: str,
    user_prompt: str,
    word_limit: int,
    user_id: str | None,
) -> dict[str, Any]:
    settings = get_settings()
    client = OpenAIClient()
    response = client.create_chat_completion(
        model=settings.OPENAI_MODEL_PRIMARY,
        fallback_model=settings.OPENAI_MODEL_FALLBACK,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=SYNTHESIS_TEMPERATURE,
        top_p=1.0,
        frequency_penalty=SYNTHESIS_FREQUENCY_PENALTY,
        presence_penalty=0.0,
        max_tokens=_max_tokens_for_section(word_limit or 0),
        feature="report_synthesis",
        user_id=user_id,
    )
    return _extract_json_payload(response)


def _generate_one_section(
    *,
    section: dict[str, Any],
    report_inputs: dict[str, Any],
    query_fn_synthesis: QueryFnSynthesis | None,
    user_id: str | None,
) -> dict[str, Any]:
    section_key = str(section.get("section_key") or "")
    label = str(section.get("label") or section_key)
    word_limit = int(section.get("word_limit") or 0)
    user_prompt = build_synthesis_user_prompt(
        report_inputs=report_inputs,
        section=section,
    )
    try:
        if query_fn_synthesis is not None:
            raw = query_fn_synthesis(
                section_key,
                REPORT_SYNTHESIS_SYSTEM_PROMPT,
                user_prompt,
            )
        else:
            raw = _call_openai_section(
                section_key=section_key,
                system_prompt=REPORT_SYNTHESIS_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                word_limit=word_limit,
                user_id=user_id,
            )
    except OpenAIServiceError as exc:
        logger.warning(
            "report_synthesis section=%s openai_error=%s",
            section_key,
            exc.category,
        )
        return {
            "section_key": section_key,
            "generation_status": "FAILED",
            "failure_reason": exc.category,
        }
    except Exception as exc:
        logger.warning(
            "report_synthesis section=%s error=%s",
            section_key,
            exc,
        )
        return {
            "section_key": section_key,
            "generation_status": "FAILED",
            "failure_reason": str(exc),
        }

    status = raw.get("generation_status")
    if status != "GENERATED":
        warnings = raw.get("warnings") or []
        reason = "; ".join(str(w) for w in warnings) if warnings else "INSUFFICIENT_INPUT"
        return {
            "section_key": section_key,
            "generation_status": "FAILED",
            "failure_reason": reason,
        }

    generated = raw.get("generated_content") or {}
    constraints = raw.get("constraints_applied") or {}
    kb = report_inputs.get("knowledge_bank") or {}
    emitted_evidence = emit_claim_granular_evidence(
        text=str(generated.get("text") or ""),
        evidence_used=list(generated.get("evidence_used") or []),
        kb_fact_keys=dict(kb.get("facts") or {}),
        kb_gap_answer_keys=dict(kb.get("gap_answers") or {}),
        section_key=section_key,
    )
    cleaned = sanitize_generated_content(
        text=str(generated.get("text") or ""),
        evidence_used=emitted_evidence,
        kb_fact_keys=dict(kb.get("facts") or {}),
        kb_gap_answer_keys=dict(kb.get("gap_answers") or {}),
    )
    if cleaned.dropped_citations:
        logger.info(
            "report_synthesis section=%s dropped_citations=%d",
            section_key,
            len(cleaned.dropped_citations),
        )
    if cleaned.remapped_citations:
        logger.info(
            "report_synthesis section=%s remapped_citations=%d",
            section_key,
            len(cleaned.remapped_citations),
        )
    if cleaned.auto_citations:
        logger.info(
            "report_synthesis section=%s auto_citations=%d",
            section_key,
            len(cleaned.auto_citations),
        )
    return build_generated_section(
        section_key=section_key,
        label=label,
        archetype=raw.get("archetype") or section.get("archetype"),
        text=cleaned.text,
        assumptions=list(generated.get("assumptions") or []),
        evidence_used=cleaned.evidence_used,
        dropped_citations=cleaned.dropped_citations,
        remapped_citations=cleaned.remapped_citations,
        auto_citations=cleaned.auto_citations,
        word_limit=word_limit,
        word_limit_respected=bool(constraints.get("word_limit_respected", True)),
    )


def _visible_sections(sections: list[Any]) -> list[dict[str, Any]]:
    visible: list[dict[str, Any]] = []
    for item in sections or []:
        if not isinstance(item, dict):
            continue
        if not item.get("section_key"):
            continue
        visible.append(item)
    return visible


def _generate_all_sections(
    *,
    sections: list[dict[str, Any]],
    report: DonorReport,
    template: FunderReportTemplate,
    db: Session,
    query_fn_synthesis: QueryFnSynthesis | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    if not sections:
        return [], []

    inputs_by_key: dict[str, dict[str, Any]] = {}
    for section in sections:
        key = str(section["section_key"])
        inputs_by_key[key] = build_report_inputs_for_section(
            db,
            report=report,
            template=template,
            section=section,
        )

    results_by_key: dict[str, dict[str, Any]] = {}
    user_id = str(report.user_id)
    max_workers = min(len(sections), get_synthesis_max_concurrency())

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                _generate_one_section,
                section=section,
                report_inputs=inputs_by_key[str(section["section_key"])],
                query_fn_synthesis=query_fn_synthesis,
                user_id=user_id,
            ): section
            for section in sections
        }
        for future in as_completed(future_map):
            section = future_map[future]
            section_key = str(section["section_key"])
            label = str(section.get("label") or section_key)
            word_limit = int(section.get("word_limit") or 0)
            try:
                result = future.result()
            except Exception as exc:  # pragma: no cover
                result = build_failed_section(
                    section_key=section_key,
                    label=label,
                    word_limit=word_limit,
                    failure_reason=str(exc),
                )
            if result.get("generation_status") == "FAILED" and "label" not in result:
                result = build_failed_section(
                    section_key=section_key,
                    label=label,
                    word_limit=word_limit,
                    failure_reason=str(result.get("failure_reason") or "GENERATION_FAILED"),
                )
            results_by_key[section_key] = result

    ordered: list[dict[str, Any]] = []
    warnings: list[str] = []
    for section in sections:
        key = str(section["section_key"])
        ordered.append(results_by_key[key])
        if results_by_key[key].get("generation_status") == "FAILED":
            warnings.append(f"section {key} failed")

    return ordered, warnings


async def synthesise_and_persist(
    db: Session,
    donor_report_id,
    *,
    query_fn_synthesis: QueryFnSynthesis | None = None,
) -> ReportSynthesisStageResult:
    """Generate missing/failed template sections and merge into donor_reports.content_json."""
    report = db.get(DonorReport, donor_report_id)
    if report is None:
        raise ReportSynthesisServiceError(
            "STOP_REPORT_NOT_FOUND",
            f"Donor report {donor_report_id} not found",
        )

    try:
        require_gate2_confirmed(report.knowledge_bank_json)
    except DomainError as exc:
        raise ReportSynthesisServiceError("STOP_GATE2", exc.message) from exc

    template = db.get(FunderReportTemplate, report.funder_report_template_id)
    if template is None:
        raise ReportSynthesisServiceError(
            "STOP_TEMPLATE_NOT_FOUND",
            "Funder template not found",
        )

    template_sections = _visible_sections(template.report_sections_json or [])
    if not template_sections:
        raise ReportSynthesisServiceError(
            "STOP_NO_SECTIONS",
            "Template has no report sections",
        )

    existing_content = dict(report.content_json or {})
    existing_by_key = sections_by_key(existing_content.get("sections") or [])
    to_generate = [
        section
        for section in template_sections
        if section_needs_synthesis(existing_by_key.get(str(section["section_key"])))
    ]

    if to_generate:
        ordered_new, warnings = await asyncio.to_thread(
            _generate_all_sections,
            sections=to_generate,
            report=report,
            template=template,
            db=db,
            query_fn_synthesis=query_fn_synthesis,
        )
        new_results_by_key = {
            str(result["section_key"]): result for result in ordered_new
        }
    else:
        warnings = []
        new_results_by_key = {}

    merged_sections = merge_synthesis_sections(
        template_sections=template_sections,
        existing_by_key=existing_by_key,
        new_results_by_key=new_results_by_key,
    )
    content_json = merge_content_json_after_synthesis(
        existing_content,
        merged_sections,
        warnings=warnings,
    )
    report.content_json = content_json

    summary = content_json.get("generation_summary") or {}
    failed = int(summary.get("failed") or 0)
    if failed > 0:
        report.status = DonorReportStatus.DEGRADED.value
    elif report.status == DonorReportStatus.DEGRADED.value:
        report.status = DonorReportStatus.DRAFT.value

    db.add(report)
    db.commit()
    db.refresh(report)

    generated = int(summary.get("generated") or 0)

    logger.info(
        "report_synthesis complete donor_report_id=%s sections=%d generated=%d failed=%d "
        "regenerated=%d",
        donor_report_id,
        len(merged_sections),
        generated,
        failed,
        len(to_generate),
    )

    return ReportSynthesisStageResult(
        section_count=len(merged_sections),
        generated=generated,
        failed=failed,
        degraded=failed > 0,
        warnings=warnings,
    )
