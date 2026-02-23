from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.ai.prompt_inputs_builder import build_prompt_inputs, select_variant_deterministic
from app.ai.prompt_runner import PROMPT_LIBRARY_VERSION, PROMPT_CONFIGS, run_prompt
from app.ai.prompts.proposal import GP_P01_SYSTEM_PROMPT, GP_P02_USER_PROMPT_TEMPLATE
from app.core.errors import ConflictError, DomainError, ForbiddenError, NotFoundError
from app.models.fit_scan import FitScan
from app.models.funding_opportunity import FundingOpportunity, OpportunityStatus
from app.models.ngo_profile import NGOProfile
from app.models.proposal import Proposal
from app.models.user_plan import UserPlan
from app.models.usage_ledger import UsageActionType, UsageLedger
from app.services.email_service import send_proposal_draft_ready_email
from app.services.profile_service import get_completeness, get_profile
from app.services.quota_service import enforce_quota, get_or_create_user_plan, record_usage

logger = logging.getLogger("proposal")

MANUAL_REQUIRED_NOTE = (
    "This section requires manual input. AI generation is not available for this item."
)
GENERATION_LIMIT_NOTE = (
    "This section exceeds the generation limit. Please write it manually."
)


class ProposalService:
    def __init__(self, db_session: Session) -> None:
        self.db = db_session

    def create_proposal(self, *, user, payload) -> Proposal:
        opportunity = self.db.get(FundingOpportunity, payload.funding_opportunity_id)
        if (
            not opportunity
            or not opportunity.is_active
            or opportunity.is_archived
            or opportunity.status not in {OpportunityStatus.READY, OpportunityStatus.PUBLISHED}
        ):
            raise NotFoundError(
                error_code="OPPORTUNITY_NOT_FOUND",
                message="Funding opportunity not found",
                status_code=404,
            )

        profile = self._load_profile_or_raise(user.id)
        status, _, missing_fields = get_completeness(self.db, user.id)
        if status != "COMPLETE":
            raise ConflictError(
                error_code="PROFILE_INCOMPLETE",
                message="Profile is incomplete",
                status_code=409,
                details={"missing_fields": missing_fields},
            )

        # Prechecks before any OpenAI call (no quota decrement here).
        enforce_quota(
            self.db,
            user.id,
            UsageActionType.PROPOSAL_CREATE.value,
            commit=False,
        )
        self._enforce_rate_limit(user.id)

        requirements = opportunity.requirements_json
        if not requirements or not isinstance(requirements, dict):
            return self._persist_degraded_proposal(
                user_id=user.id,
                funding_opportunity_id=opportunity.id,
                fit_scan_id=payload.fit_scan_id,
                selected_variant_id=payload.selected_variant_id,
                reason="missing_requirements_json",
            )
        if not _requirements_structurally_valid(requirements):
            return self._persist_degraded_proposal(
                user_id=user.id,
                funding_opportunity_id=opportunity.id,
                fit_scan_id=payload.fit_scan_id,
                selected_variant_id=payload.selected_variant_id,
                reason="invalid_requirements_structure",
            )

        prompt_inputs = build_prompt_inputs(profile, opportunity, payload.model_dump())
        derived = prompt_inputs["prompt_inputs"]["derived"]
        selected_variant = derived.get("selected_variant") or {}
        if not selected_variant:
            return self._persist_degraded_proposal(
                user_id=user.id,
                funding_opportunity_id=opportunity.id,
                fit_scan_id=payload.fit_scan_id,
                selected_variant_id=payload.selected_variant_id,
                reason="invalid_requirements_structure",
            )

        submission_items = selected_variant.get("submission_items")
        if not isinstance(submission_items, list) or not submission_items:
            return self._persist_degraded_proposal(
                user_id=user.id,
                funding_opportunity_id=opportunity.id,
                fit_scan_id=payload.fit_scan_id,
                selected_variant_id=payload.selected_variant_id,
                reason="invalid_requirements_structure",
            )

        fit_scan_output = self._load_fit_scan_output(user.id, payload.fit_scan_id)
        sections, summary = self._generate_sections(
            prompt_inputs=prompt_inputs,
            fit_scan_output=fit_scan_output,
            submission_items=submission_items,
        )

        if summary["generated"] <= 0:
            raise DomainError(
                error_code="PROPOSAL_GENERATION_FAILED",
                message="All proposal sections failed to generate",
                status_code=500,
            )

        plan_name = _get_plan_name(self.db, user.id)
        proposal = Proposal(
            user_id=user.id,
            funding_opportunity_id=opportunity.id,
            fit_scan_id=payload.fit_scan_id,
            plan_at_creation=plan_name,
            prompt_version=PROMPT_LIBRARY_VERSION,
            selected_variant_id=derived.get("selected_variant_id"),
            content_json={"sections": sections, "generation_summary": summary},
        )

        try:
            with self.db.begin():
                # GUARDRAILS: atomic quota decrement with persistence.
                self.db.add(proposal)
                self.db.flush()
                record_usage(
                    self.db,
                    user.id,
                    UsageActionType.PROPOSAL_CREATE.value,
                    idempotency_key=str(uuid.uuid4()),
                    commit=False,
                )
        except DomainError:
            raise
        except Exception as exc:  # pragma: no cover - DB-level failure
            self.db.rollback()
            raise DomainError(
                error_code="PROPOSAL_GENERATION_FAILED",
                message="Failed to persist proposal",
                status_code=500,
            ) from exc

        self.db.refresh(proposal)
        try:
            send_proposal_draft_ready_email(
                self.db,
                user=user,
                proposal_id=proposal.id,
                opportunity_title=opportunity.title,
                event_key=f"proposal:{proposal.id}:draft_ready",
            )
        except Exception:
            # Non-blocking by contract: proposal creation must still succeed.
            logger.exception("proposal_draft_ready_email_failed proposal_id=%s", proposal.id)
        return proposal

    def _persist_degraded_proposal(
        self,
        *,
        user_id: uuid.UUID,
        funding_opportunity_id: uuid.UUID,
        fit_scan_id: uuid.UUID | None,
        selected_variant_id: str | None,
        reason: str,
    ) -> Proposal:
        plan_name = _get_plan_name(self.db, user_id)
        degraded_content = {
            "sections": [
                {
                    "submission_item_id": "requirements_review",
                    "label": "Requirements Review",
                    "generation_status": "MANUAL_REQUIRED",
                    "archetype": None,
                    "content": {
                        "text": "To be completed manually",
                        "assumptions": [],
                        "evidence_used": [],
                    },
                    "failure_reason": reason,
                    "constraints_applied": {
                        "word_limit": 0,
                        "word_limit_respected": True,
                    },
                }
            ],
            "generation_summary": {
                "total_items": 1,
                "generated": 0,
                "failed": 0,
                "manual_required": 1,
                "warnings": [reason],
            },
            "status": "DEGRADED",
        }
        proposal = Proposal(
            user_id=user_id,
            funding_opportunity_id=funding_opportunity_id,
            fit_scan_id=fit_scan_id,
            plan_at_creation=plan_name,
            prompt_version=PROMPT_LIBRARY_VERSION,
            selected_variant_id=selected_variant_id,
            content_json=degraded_content,
            status="DRAFT",
        )
        try:
            with self.db.begin():
                self.db.add(proposal)
                self.db.flush()
        except Exception as exc:  # pragma: no cover - DB-level failure
            self.db.rollback()
            raise DomainError(
                error_code="PROPOSAL_GENERATION_FAILED",
                message="Failed to persist proposal",
                status_code=500,
            ) from exc
        self.db.refresh(proposal)
        return proposal

    def get_proposal(self, *, user, proposal_id: uuid.UUID) -> Proposal:
        proposal = self.db.get(Proposal, proposal_id)
        if not proposal:
            raise NotFoundError(
                error_code="PROPOSAL_NOT_FOUND",
                message="Proposal not found",
                status_code=404,
            )
        if str(proposal.user_id) != str(user.id):
            raise ForbiddenError(
                error_code="FORBIDDEN",
                message="Forbidden",
                status_code=403,
            )
        return proposal

    def list_proposals(self, *, user, limit: int) -> list[Proposal]:
        statement = (
            select(Proposal)
            .where(Proposal.user_id == user.id)
            .order_by(Proposal.created_at.desc())
            .limit(limit)
        )
        return list(self.db.execute(statement).scalars().all())

    def regenerate_proposal(self, *, user, proposal_id: uuid.UUID) -> Proposal:
        proposal = self.get_proposal(user=user, proposal_id=proposal_id)
        plan_name = _get_plan_name(self.db, user.id)
        if plan_name == "FREE":
            raise ForbiddenError(
                error_code="REGENERATION_NOT_ALLOWED",
                message="Regeneration is not allowed on the Free plan.",
                status_code=403,
            )
        if proposal.regeneration_count >= 3:
            raise ForbiddenError(
                error_code="REGENERATION_LIMIT_REACHED",
                message="Regeneration limit reached for this proposal.",
                status_code=403,
            )

        opportunity = self.db.get(FundingOpportunity, proposal.funding_opportunity_id)
        if (
            not opportunity
            or not opportunity.is_active
            or opportunity.is_archived
            or opportunity.status not in {OpportunityStatus.READY, OpportunityStatus.PUBLISHED}
        ):
            raise NotFoundError(
                error_code="OPPORTUNITY_NOT_FOUND",
                message="Funding opportunity not found",
                status_code=404,
            )

        profile = self._load_profile_or_raise(user.id)

        requirements = opportunity.requirements_json
        if not requirements or not isinstance(requirements, dict):
            raise DomainError(
                error_code="REQUIREMENTS_INVALID",
                message="Opportunity requirements are incomplete; proposal cannot be generated yet.",
                status_code=422,
                details={"reason": "missing_requirements_json"},
            )
        if not _requirements_structurally_valid(requirements):
            raise DomainError(
                error_code="REQUIREMENTS_INVALID",
                message="Opportunity requirements are incomplete; proposal cannot be generated yet.",
                status_code=422,
                details={"reason": "invalid_requirements_structure"},
            )

        user_inputs = {"selected_variant_id": proposal.selected_variant_id}
        prompt_inputs = build_prompt_inputs(profile, opportunity, user_inputs)
        derived = prompt_inputs["prompt_inputs"]["derived"]
        selected_variant = derived.get("selected_variant") or {}
        if not selected_variant:
            raise DomainError(
                error_code="REQUIREMENTS_INVALID",
                message="Opportunity requirements are incomplete; proposal cannot be generated yet.",
                status_code=422,
                details={"reason": "invalid_requirements_structure"},
            )

        submission_items = selected_variant.get("submission_items")
        if not isinstance(submission_items, list) or not submission_items:
            raise DomainError(
                error_code="REQUIREMENTS_INVALID",
                message="Opportunity requirements are incomplete; proposal cannot be generated yet.",
                status_code=422,
                details={"reason": "invalid_requirements_structure"},
            )

        content_json = proposal.content_json or {}
        existing_sections = content_json.get("sections")
        if not isinstance(existing_sections, list) or not existing_sections:
            raise DomainError(
                error_code="PROPOSAL_REGEN_FAILED",
                message="Proposal content is missing or invalid.",
                status_code=500,
            )

        regenerated_sections, summary = self._regenerate_sections(
            prompt_inputs=prompt_inputs,
            submission_items=submission_items,
            existing_sections=existing_sections,
        )
        if summary["generated"] <= 0:
            raise DomainError(
                error_code="PROPOSAL_REGEN_FAILED",
                message="All proposal sections failed to regenerate",
                status_code=500,
            )

        proposal.content_json = {
            "sections": regenerated_sections,
            "generation_summary": summary,
        }
        proposal.version = int(proposal.version) + 1
        proposal.regeneration_count = int(proposal.regeneration_count) + 1
        proposal.updated_at = datetime.now(timezone.utc)

        try:
            with self.db.begin():
                self.db.add(proposal)
                self.db.flush()
                record_usage(
                    self.db,
                    user.id,
                    UsageActionType.PROPOSAL_REGEN.value,
                    idempotency_key=str(uuid.uuid4()),
                    commit=False,
                )
        except DomainError:
            raise
        except Exception as exc:  # pragma: no cover - DB-level failure
            self.db.rollback()
            raise DomainError(
                error_code="PROPOSAL_REGEN_FAILED",
                message="Failed to persist regenerated proposal",
                status_code=500,
            ) from exc

        self.db.refresh(proposal)
        return proposal

    def _load_profile_or_raise(self, user_id: uuid.UUID) -> NGOProfile:
        try:
            return get_profile(self.db, user_id)
        except NotFoundError as exc:
            raise ConflictError(
                error_code="PROFILE_INCOMPLETE",
                message="Profile is incomplete",
                status_code=409,
                details={"missing_fields": _missing_profile_fields()},
            ) from exc

    def _load_fit_scan_output(self, user_id: uuid.UUID, fit_scan_id: uuid.UUID | None) -> dict:
        if not fit_scan_id:
            return {}
        fit_scan = self.db.get(FitScan, fit_scan_id)
        if not fit_scan:
            raise NotFoundError(
                error_code="FIT_SCAN_NOT_FOUND",
                message="Fit Scan not found",
                status_code=404,
            )
        if str(fit_scan.user_id) != str(user_id):
            raise ForbiddenError(
                error_code="FORBIDDEN",
                message="Forbidden",
                status_code=403,
            )
        return fit_scan.result_json or {}

    def _enforce_rate_limit(self, user_id: uuid.UUID) -> None:
        plan = get_or_create_user_plan(self.db, user_id)
        if plan.plan_name not in {"GROWTH", "IMPACT"}:
            return
        latest = self.db.execute(
            select(UsageLedger)
            .where(
                UsageLedger.user_id == user_id,
                UsageLedger.event_type == UsageActionType.PROPOSAL_CREATE.value,
            )
            .order_by(desc(UsageLedger.occurred_at))
            .limit(1)
        ).scalar_one_or_none()
        if not latest:
            return
        occurred_at = latest.occurred_at
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        if occurred_at >= datetime.now(timezone.utc) - timedelta(minutes=10):
            raise DomainError(
                error_code="RATE_LIMITED",
                message="Proposal creation is rate limited",
                status_code=429,
            )

    def _generate_sections(
        self,
        *,
        prompt_inputs: dict[str, Any],
        fit_scan_output: dict[str, Any],
        submission_items: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        generatable_items = [
            item for item in submission_items if item.get("generation_allowed") is True
        ]
        items_to_generate = generatable_items[:5]
        manual_due_to_cap = {item.get("item_id") for item in generatable_items[5:]}

        warnings: list[str] = []
        _, variant_warning = select_variant_deterministic(
            prompt_inputs["prompt_inputs"].get("requirements"),
            prompt_inputs["prompt_inputs"].get("ngo", {}),
            prompt_inputs["prompt_inputs"].get("user", {}),
        )
        if variant_warning:
            warnings.append(variant_warning)

        sections: list[dict[str, Any]] = []
        generated = 0
        failed = 0
        manual_required = 0

        for item in submission_items:
            item_id = item.get("item_id")
            label = item.get("label") or ""
            format_constraints = item.get("format_constraints") or {}
            word_limit = int(format_constraints.get("word_limit") or 0)

            if item.get("generation_allowed") is not True:
                manual_required += 1
                sections.append(
                    _manual_section(
                        item_id,
                        label,
                        word_limit,
                        MANUAL_REQUIRED_NOTE,
                    )
                )
                continue

            if item_id in manual_due_to_cap:
                manual_required += 1
                sections.append(
                    _manual_section(
                        item_id,
                        label,
                        word_limit,
                        GENERATION_LIMIT_NOTE,
                    )
                )
                continue

            result = self._generate_item(
                prompt_inputs=prompt_inputs,
                fit_scan_output=fit_scan_output,
                submission_item=item,
            )
            status = result.get("generation_status")
            if status == "GENERATED":
                generated += 1
                sections.append(_generated_section(item, result))
            elif status == "INSUFFICIENT_INPUT":
                failed += 1
                sections.append(
                    _failed_section(
                        item_id,
                        label,
                        word_limit,
                        "INSUFFICIENT_INPUT",
                    )
                )
            elif status == "UPLOAD_REQUIRED":
                manual_required += 1
                sections.append(
                    _manual_section(
                        item_id,
                        label,
                        word_limit,
                        MANUAL_REQUIRED_NOTE,
                    )
                )
            else:
                failed += 1
                sections.append(
                    _failed_section(
                        item_id,
                        label,
                        word_limit,
                        "AI_SERVICE_ERROR",
                    )
                )

            warnings.extend(result.get("warnings") or [])

        summary = {
            "total_items": len(submission_items),
            "generated": generated,
            "failed": failed,
            "manual_required": manual_required,
            "warnings": warnings,
        }
        return sections, summary

    def _regenerate_sections(
        self,
        *,
        prompt_inputs: dict[str, Any],
        submission_items: list[dict[str, Any]],
        existing_sections: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        items_by_id = {item.get("item_id"): item for item in submission_items}
        generatable_items = [
            item for item in submission_items if item.get("generation_allowed") is True
        ]
        allowed_ids = {item.get("item_id") for item in generatable_items[:5]}

        warnings: list[str] = []
        regenerated: list[dict[str, Any]] = []
        generated = 0
        failed = 0
        manual_required = 0

        for section in existing_sections:
            status = section.get("generation_status")
            item_id = section.get("submission_item_id")
            label = section.get("label") or ""
            submission_item = items_by_id.get(item_id)

            if status == "MANUAL_REQUIRED":
                manual_required += 1
                regenerated.append(section)
                continue

            if not submission_item:
                raise DomainError(
                    error_code="REQUIREMENTS_INVALID",
                    message="Opportunity requirements are incomplete; proposal cannot be generated yet.",
                    status_code=422,
                    details={"reason": "invalid_requirements_structure"},
                )

            format_constraints = submission_item.get("format_constraints") or {}
            word_limit = int(format_constraints.get("word_limit") or 0)

            if (
                submission_item.get("generation_allowed") is not True
                or item_id not in allowed_ids
            ):
                manual_required += 1
                regenerated.append(
                    _manual_section(
                        item_id,
                        label,
                        word_limit,
                        GENERATION_LIMIT_NOTE
                        if item_id not in allowed_ids
                        else MANUAL_REQUIRED_NOTE,
                    )
                )
                continue

            result = self._generate_item(
                prompt_inputs=prompt_inputs,
                fit_scan_output={},
                submission_item=submission_item,
            )
            result_status = result.get("generation_status")
            if result_status == "GENERATED":
                generated += 1
                regenerated.append(_generated_section(submission_item, result))
            elif result_status == "INSUFFICIENT_INPUT":
                failed += 1
                regenerated.append(
                    _failed_section(
                        item_id,
                        label,
                        word_limit,
                        "INSUFFICIENT_INPUT",
                    )
                )
            elif result_status == "UPLOAD_REQUIRED":
                manual_required += 1
                regenerated.append(
                    _manual_section(
                        item_id,
                        label,
                        word_limit,
                        MANUAL_REQUIRED_NOTE,
                    )
                )
            else:
                failed += 1
                regenerated.append(
                    _failed_section(
                        item_id,
                        label,
                        word_limit,
                        "AI_SERVICE_ERROR",
                    )
                )

            warnings.extend(result.get("warnings") or [])

        summary = {
            "total_items": len(existing_sections),
            "generated": generated,
            "failed": failed,
            "manual_required": manual_required,
            "warnings": warnings,
        }
        return regenerated, summary

    def _generate_item(
        self,
        *,
        prompt_inputs: dict[str, Any],
        fit_scan_output: dict[str, Any],
        submission_item: dict[str, Any],
    ) -> dict[str, Any]:
        prompt_id = "GP-P02"
        config = PROMPT_CONFIGS[prompt_id]
        prompt_inputs_json = json.dumps(prompt_inputs, separators=(",", ":"), ensure_ascii=True)
        fit_scan_output_json = json.dumps(
            fit_scan_output, separators=(",", ":"), ensure_ascii=True
        )
        submission_item_json = json.dumps(
            submission_item, separators=(",", ":"), ensure_ascii=True
        )
        user_prompt = GP_P02_USER_PROMPT_TEMPLATE.format(
            prompt_inputs_json=prompt_inputs_json,
            fit_scan_output_json=fit_scan_output_json,
            submission_item_json=submission_item_json,
        )
        try:
            return run_prompt(
                prompt_id=prompt_id,
                system_prompt=GP_P01_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=float(config["temperature"]),
                top_p=float(config["top_p"]),
                frequency_penalty=float(config["frequency_penalty"]),
                presence_penalty=float(config["presence_penalty"]),
                max_tokens=int(config["max_tokens"]),
            )
        except DomainError as exc:
            return {"generation_status": "FAILED", "warnings": [exc.error_code]}


def _generated_section(item: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    format_constraints = item.get("format_constraints") or {}
    word_limit = int(format_constraints.get("word_limit") or 0)
    generated_content = result.get("generated_content") or {}
    constraints = result.get("constraints_applied") or {}
    return {
        "submission_item_id": item.get("item_id"),
        "label": item.get("label") or "",
        "generation_status": "GENERATED",
        "archetype": result.get("archetype"),
        "content": {
            "text": generated_content.get("text") or "",
            "assumptions": generated_content.get("assumptions") or [],
            "evidence_used": generated_content.get("evidence_used") or [],
        },
        "failure_reason": None,
        "constraints_applied": {
            "word_limit": word_limit,
            "word_limit_respected": bool(constraints.get("word_limit_respected", True)),
        },
    }


def _manual_section(
    item_id: str | None,
    label: str,
    word_limit: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "submission_item_id": item_id,
        "label": label,
        "generation_status": "MANUAL_REQUIRED",
        "archetype": None,
        "content": {"text": "", "assumptions": [], "evidence_used": []},
        "failure_reason": reason,
        "constraints_applied": {
            "word_limit": word_limit,
            "word_limit_respected": True,
        },
    }


def _failed_section(
    item_id: str | None,
    label: str,
    word_limit: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "submission_item_id": item_id,
        "label": label,
        "generation_status": "FAILED",
        "archetype": None,
        "content": {"text": "", "assumptions": [], "evidence_used": []},
        "failure_reason": reason,
        "constraints_applied": {
            "word_limit": word_limit,
            "word_limit_respected": False,
        },
    }


def _missing_profile_fields() -> list[str]:
    return [
        "organization_name",
        "country_of_registration",
        "mission_statement",
        "focus_sectors",
        "geographic_areas_of_work",
        "target_groups",
        "past_projects",
    ]


def _get_plan_name(db: Session, user_id: uuid.UUID) -> str:
    plan = db.execute(select(UserPlan).where(UserPlan.user_id == user_id)).scalar_one_or_none()
    return plan.plan_name if plan else "FREE"


def _degraded_payload(
    code: str,
    message: str,
    missing_items: list[str],
    next_actions: list[str],
) -> dict[str, Any]:
    return {
        "status": "DEGRADED",
        "error_code": code,
        "message": message,
        "missing_items": missing_items,
        "next_actions": next_actions,
    }


def _requirements_structurally_valid(requirements: dict) -> bool:
    variants = requirements.get("variants")
    submission_items = requirements.get("submission_items")
    if not variants and not submission_items:
        return False
    if variants is not None and not isinstance(variants, list):
        return False
    if submission_items is not None and not isinstance(submission_items, list):
        return False
    if not variants:
        return False
    return True
