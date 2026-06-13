"""F1 report section synthesis — persist to donor_reports.content_json."""

from __future__ import annotations

import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from typing import Any, Callable

from sqlalchemy import text
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
from app.reports.gap.section_visibility import visible_sections_for_context
from app.reports.services.gate_preconditions import require_gate1_confirmed, require_gate2_confirmed
from app.reports.services.report_inputs_builder import (
    build_report_inputs_for_section,
    section_has_synthesizable_inputs,
)
from app.reports.services.section_prose import (
    FAILURE_EMPTY_PROSE,
    build_insufficient_data_section,
    has_non_empty_prose,
)
from app.reports.services.synthesis_claim_binding import resolve_structured_synthesis
from app.reports.services.synthesis_citation_emission import emit_claim_granular_evidence
from app.reports.services.synthesis_output_hygiene import (
    sanitize_generated_content,
    sanitize_json_for_postgres,
)

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
    openai_input_tokens: int = 0
    openai_output_tokens: int = 0


def _extract_usage_counts(response: dict[str, Any]) -> tuple[int, int]:
    usage = response.get("usage") or {}
    if not isinstance(usage, dict):
        return 0, 0
    inp = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
    out = usage.get("completion_tokens") or usage.get("output_tokens") or 0
    return int(inp or 0), int(out or 0)


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
) -> tuple[dict[str, Any], int, int]:
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
    return _extract_json_payload(response), *_extract_usage_counts(response)


def _generate_one_section(
    *,
    section: dict[str, Any],
    report_inputs: dict[str, Any],
    knowledge_bank_json: dict[str, Any],
    report_context: dict[str, Any],
    query_fn_synthesis: QueryFnSynthesis | None,
    user_id: str | None,
) -> tuple[dict[str, Any], int, int]:
    section_key = str(section.get("section_key") or "")
    label = str(section.get("label") or section_key)
    word_limit = int(section.get("word_limit") or 0)

    has_inputs = section_has_synthesizable_inputs(
        knowledge_bank_json,
        section,
        report_context=report_context,
    )
    if not has_inputs:
        logger.info(
            "report_synthesis section=%s insufficient_data preflight skip",
            section_key,
        )
        return build_insufficient_data_section(section=section), 0, 0

    user_prompt = build_synthesis_user_prompt(
        report_inputs=report_inputs,
        section=section,
    )
    input_tokens = output_tokens = 0
    try:
        if query_fn_synthesis is not None:
            raw = query_fn_synthesis(
                section_key,
                REPORT_SYNTHESIS_SYSTEM_PROMPT,
                user_prompt,
            )
        else:
            raw, input_tokens, output_tokens = _call_openai_section(
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
        }, input_tokens, output_tokens
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
        }, input_tokens, output_tokens

    status = raw.get("generation_status")
    if status != "GENERATED":
        warnings = raw.get("warnings") or []
        reason = "; ".join(str(w) for w in warnings) if warnings else "INSUFFICIENT_INPUT"
        return build_failed_section(
            section_key=section_key,
            label=label,
            word_limit=word_limit,
            failure_reason=reason,
        ), input_tokens, output_tokens

    generated = raw.get("generated_content") or {}
    constraints = raw.get("constraints_applied") or {}
    kb = report_inputs.get("knowledge_bank") or {}

    if get_settings().SYNTHESIS_CITATION_FALLBACK:
        logger.info(
            "report_synthesis section=%s citation_mode=legacy_fallback",
            section_key,
        )
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
        if cleaned.humaniser_violations:
            logger.info(
                "report_synthesis section=%s humaniser_violations=%s",
                section_key,
                cleaned.humaniser_violations,
            )
        if not has_non_empty_prose({"content": {"text": cleaned.text}}):
            return build_failed_section(
                section_key=section_key,
                label=label,
                word_limit=word_limit,
                failure_reason=FAILURE_EMPTY_PROSE,
            ), input_tokens, output_tokens
        return build_generated_section(
            section_key=section_key,
            label=label,
            archetype=raw.get("archetype") or section.get("archetype"),
            text=cleaned.text,
            assumptions=list(generated.get("assumptions") or []),
            evidence_used=cleaned.evidence_used,
            citation_mode="legacy_fallback",
            dropped_citations=cleaned.dropped_citations,
            remapped_citations=cleaned.remapped_citations,
            auto_citations=cleaned.auto_citations,
            word_limit=word_limit,
            word_limit_respected=bool(constraints.get("word_limit_respected", True)),
        ), input_tokens, output_tokens

    bind_outcome = resolve_structured_synthesis(
        claims=list(generated.get("claims") or []),
        text=str(generated.get("text") or ""),
        knowledge_bank=kb,
    )
    if not bind_outcome.ok:
        return build_failed_section(
            section_key=section_key,
            label=label,
            word_limit=word_limit,
            failure_reason=str(bind_outcome.failure_reason or "BIND_FAILED"),
        ), input_tokens, output_tokens

    bound = bind_outcome.content
    assert bound is not None
    if not has_non_empty_prose({"content": {"text": bound.text}}):
        return build_failed_section(
            section_key=section_key,
            label=label,
            word_limit=word_limit,
            failure_reason=FAILURE_EMPTY_PROSE,
        ), input_tokens, output_tokens
    return build_generated_section(
        section_key=section_key,
        label=label,
        archetype=raw.get("archetype") or section.get("archetype"),
        text=bound.text,
        assumptions=list(generated.get("assumptions") or []),
        evidence_used=bound.evidence_used,
        claims=bound.claims,
        citation_mode="structured",
        omitted_claims=bound.omitted_claims or None,
        structured_bind_status=bound.structured_bind_status,
        word_limit=word_limit,
        word_limit_respected=bool(constraints.get("word_limit_respected", True)),
    ), input_tokens, output_tokens


def _generate_all_sections(
    *,
    sections: list[dict[str, Any]],
    report: DonorReport,
    template: FunderReportTemplate,
    db: Session,
    report_context: dict[str, Any],
    query_fn_synthesis: QueryFnSynthesis | None,
) -> tuple[list[dict[str, Any]], list[str], int, int]:
    if not sections:
        return [], [], 0, 0

    kb_json = dict(report.knowledge_bank_json or {})
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
    total_input_tokens = 0
    total_output_tokens = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {
            executor.submit(
                _generate_one_section,
                section=section,
                report_inputs=inputs_by_key[str(section["section_key"])],
                knowledge_bank_json=kb_json,
                report_context=report_context,
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
                result, in_tok, out_tok = future.result()
            except Exception as exc:  # pragma: no cover
                result = build_failed_section(
                    section_key=section_key,
                    label=label,
                    word_limit=word_limit,
                    failure_reason=str(exc),
                )
                in_tok = out_tok = 0
            total_input_tokens += in_tok
            total_output_tokens += out_tok
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

    return ordered, warnings, total_input_tokens, total_output_tokens


def _acquire_synthesis_lock(db: Session, donor_report_id) -> None:
    """PostgreSQL advisory lock — single-flight synthesis per report (F-5)."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"),
        {"lock_key": f"report_synthesis:{donor_report_id}"},
    )


async def synthesise_and_persist(
    db: Session,
    donor_report_id,
    *,
    query_fn_synthesis: QueryFnSynthesis | None = None,
    synthesis_mode: str = "final",
) -> ReportSynthesisStageResult:
    """Generate missing/failed template sections and merge into donor_reports.content_json."""
    _acquire_synthesis_lock(db, donor_report_id)
    report = db.get(DonorReport, donor_report_id)
    if report is None:
        raise ReportSynthesisServiceError(
            "STOP_REPORT_NOT_FOUND",
            f"Donor report {donor_report_id} not found",
        )

    if synthesis_mode == "draft":
        try:
            require_gate1_confirmed(report.knowledge_bank_json)
        except DomainError as exc:
            raise ReportSynthesisServiceError("STOP_GATE1", exc.message) from exc
    else:
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

    report_context = (report.gap_analysis_json or {}).get("report_context") or {
        "report_type": "annual"
    }
    template_sections = visible_sections_for_context(
        template.report_sections_json or [],
        report_context=report_context,
        include_funder_owned=False,
    )
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

    total_input_tokens = 0
    total_output_tokens = 0
    if to_generate:
        ordered_new, warnings, total_input_tokens, total_output_tokens = await asyncio.to_thread(
            _generate_all_sections,
            sections=to_generate,
            report=report,
            template=template,
            db=db,
            report_context=report_context,
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
    content_json = sanitize_json_for_postgres(
        merge_content_json_after_synthesis(
            existing_content,
            merged_sections,
            warnings=warnings,
        )
    )
    if synthesis_mode == "draft":
        content_json["synthesis_mode"] = "draft"
    elif content_json.get("synthesis_mode") == "draft":
        content_json["synthesis_mode"] = "final"
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
        openai_input_tokens=total_input_tokens,
        openai_output_tokens=total_output_tokens,
    )
