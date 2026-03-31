from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.core.errors import DomainError
from app.models.funding_opportunity import FundingOpportunity
from app.models.ngo_profile import NGOProfile

logger = logging.getLogger("prompt_inputs_builder")


def build_prompt_inputs(
    ngo_profile: NGOProfile | None,
    funding_opportunity: FundingOpportunity | None,
    user_inputs: dict | None = None,
) -> dict[str, Any]:
    if ngo_profile is None or funding_opportunity is None:
        raise DomainError(
            error_code="PROMPT_INPUTS_INVALID",
            message="Missing NGO profile or funding opportunity",
            status_code=500,
        )

    ngo = _build_ngo_payload(ngo_profile)
    opportunity = _build_opportunity_payload(funding_opportunity)
    requirements = _normalize_requirements(funding_opportunity.requirements_json)
    user = _build_user_payload(user_inputs)
    derived = _build_derived_payload(ngo, opportunity, requirements, user)
    _apply_opportunity_aliases(opportunity, derived, requirements)
    # TEMP diagnostic: verify derived keys include selected variant fields.
    logger.debug("prompt_inputs_derived_keys=%s", sorted(derived.keys()))

    return {
        "prompt_inputs": {
            "ngo": ngo,
            "opportunity": opportunity,
            "requirements": requirements,
            "user": user,
            "derived": derived,
        }
    }


def _build_ngo_payload(profile: NGOProfile) -> dict[str, Any]:
    ngo = {
        "organization_name": profile.organization_name,
        "country_of_registration": profile.country_of_registration,
        "website": profile.website,
        "mission_statement": profile.mission_statement,
        "focus_sectors": profile.focus_sectors or [],
        "geographic_areas_of_work": profile.geographic_areas_of_work or [],
        "target_groups": profile.target_groups or [],
        "past_projects": profile.past_projects or [],
        "annual_budget_amount": _coerce_number(profile.annual_budget_amount),
        "annual_budget_currency": profile.annual_budget_currency or "USD",
        "full_time_staff": profile.full_time_staff,
        "year_of_establishment": profile.year_of_establishment,
        "contact_person_name": profile.contact_person_name,
        "contact_email": profile.contact_email,
        "monitoring_and_evaluation_practices": profile.monitoring_and_evaluation_practices,
        "funders_worked_with_before": profile.funders_worked_with_before or [],
    }

    # Legacy alias support (Section 7).
    ngo["country"] = ngo["country_of_registration"]
    ngo["beneficiaries"] = ngo["target_groups"]
    ngo["focus_areas"] = ngo["focus_sectors"]
    ngo["sectors"] = ngo["focus_sectors"]
    ngo["geographic_areas"] = ngo["geographic_areas_of_work"]
    ngo["annual_budget_range"] = ngo["annual_budget_amount"]
    ngo["organization_type"] = "NGO"
    return ngo


def _build_opportunity_payload(opportunity: FundingOpportunity) -> dict[str, Any]:
    return {
        "id": str(opportunity.id),
        "source_url": opportunity.source_url,
        "application_url": opportunity.application_url,
        "title": opportunity.title,
        "donor_organization": opportunity.donor_organization,
        "funding_type": opportunity.funding_type,
        "applicant_type": opportunity.applicant_type.value
        if hasattr(opportunity.applicant_type, "value")
        else opportunity.applicant_type,
        "location_text": opportunity.location_text,
        "focus_areas": opportunity.focus_areas,
        "deadline_type": opportunity.deadline_type.value
        if hasattr(opportunity.deadline_type, "value")
        else opportunity.deadline_type,
        "application_deadline": opportunity.application_deadline.isoformat()
        if opportunity.application_deadline
        else None,
        "currency": opportunity.currency,
        "amount_min": _coerce_number(opportunity.amount_min),
        "amount_max": _coerce_number(opportunity.amount_max),
        "total_funding_available": _coerce_number(opportunity.total_funding_available),
        "short_summary": opportunity.short_summary,
        "overview_text": opportunity.overview_text,
        "eligibility_criteria": opportunity.eligibility_criteria,
        "application_process": opportunity.application_process,
        "contact_information": opportunity.contact_information,
        "organization_types": opportunity.organization_types,
        "geographic_focus": opportunity.geographic_focus,
    }


def _normalize_requirements(requirements: Any) -> dict | None:
    if not requirements or not isinstance(requirements, dict):
        return None
    return requirements


def _build_user_payload(user_inputs: dict | None) -> dict[str, Any]:
    user_inputs = user_inputs or {}
    overrides = user_inputs.get("user_overrides")
    if overrides is None:
        overrides = {
            "preferred_focus": [],
            "deprioritise_focus": [],
            "tone_preference": "STANDARD",
            "must_include_points": [],
            "must_avoid_points": [],
        }
    return {
        "selected_variant_id": user_inputs.get("selected_variant_id"),
        "user_goal": user_inputs.get("user_goal"),
        "user_overrides": overrides,
        "uploaded_documents_index": [],
    }


def _build_derived_payload(
    ngo: dict[str, Any],
    opportunity: dict[str, Any],
    requirements: dict | None,
    user: dict[str, Any],
) -> dict[str, Any]:
    today = datetime.now(timezone.utc).date()
    selected_variant_id, _ = select_variant_deterministic(requirements, ngo, user)
    selected_variant = _extract_variant(requirements, selected_variant_id)
    variant_lookup_warning = None
    if selected_variant_id and not selected_variant:
        variant_lookup_warning = (
            f"SELECTED_VARIANT_NOT_FOUND:{selected_variant_id}"
        )
        logger.warning(variant_lookup_warning)

    return {
        "today_utc_date": today.isoformat(),
        "uploads_supported": False,
        "grant_amount_display": _grant_amount_display(opportunity),
        "annual_budget_display": _annual_budget_display(ngo),
        "opportunity_priorities_phrases": _opportunity_priorities_phrases(
            requirements, opportunity
        ),
        "selected_variant_id": selected_variant_id,
        "selected_variant": selected_variant or None,
        "selected_variant_warning": variant_lookup_warning,
        "deadline_days_remaining": _deadline_days_remaining(opportunity, today),
        "applicant_type": "NGO",
    }


def _extract_variant(requirements: dict | None, variant_id: str | None) -> dict:
    if not requirements or not variant_id:
        return {}
    for variant in requirements.get("variants") or []:
        if variant.get("variant_id") == variant_id:
            return variant
    return {}


def _deadline_days_remaining(opportunity: dict[str, Any], today: date) -> int | None:
    if opportunity.get("deadline_type") != "FIXED":
        return None
    deadline_str = opportunity.get("application_deadline")
    if not deadline_str:
        return None
    deadline = date.fromisoformat(deadline_str)
    return (deadline - today).days


def _opportunity_priorities_phrases(
    requirements: dict | None, opportunity: dict[str, Any]
) -> list[str]:
    phrases: list[str] = []
    if requirements:
        for variant in requirements.get("variants") or []:
            themes = variant.get("eligibility_rules", {}).get("themes_required") or []
            phrases.extend(themes)
        review = requirements.get("global_notes", {}).get("review_criteria") or []
        phrases.extend(review)
    focus_areas = opportunity.get("focus_areas") or ""
    if isinstance(focus_areas, str) and focus_areas:
        phrases.extend([area.strip() for area in focus_areas.split(",") if area.strip()])

    seen = set()
    deduped: list[str] = []
    for phrase in phrases:
        if phrase and phrase not in seen:
            seen.add(phrase)
            deduped.append(phrase)
    return deduped


def _grant_amount_display(opportunity: dict[str, Any]) -> str:
    currency = opportunity.get("currency")
    amount_min = opportunity.get("amount_min")
    amount_max = opportunity.get("amount_max")
    total = opportunity.get("total_funding_available")

    if currency and amount_min is not None and amount_max is not None:
        return f"{currency} {_format_number(amount_min)}–{_format_number(amount_max)}"
    if currency and amount_max is not None:
        return f"Up to {currency} {_format_number(amount_max)}"
    if currency and amount_min is not None:
        return f"From {currency} {_format_number(amount_min)}"
    if currency and total is not None:
        return f"{currency} {_format_number(total)} total"
    return "Amount not specified"


def _annual_budget_display(ngo: dict[str, Any]) -> str:
    amount = ngo.get("annual_budget_amount")
    currency = ngo.get("annual_budget_currency")
    if amount is not None and currency:
        return f"{currency} {_format_number(amount)}"
    return ""


def select_variant_deterministic(
    requirements: dict | None, ngo: dict[str, Any], user: dict[str, Any]
) -> tuple[str | None, str | None]:
    if not requirements:
        return None, None
    variants = requirements.get("variants") or []
    if not variants:
        return None, None

    user_selected = user.get("selected_variant_id")
    if user_selected and any(
        variant.get("variant_id") == user_selected for variant in variants
    ):
        return user_selected, None

    ngo_org_type = ngo.get("organization_type") or "NGO"
    applicant_matches = [
        variant
        for variant in variants
        if variant.get("eligibility_rules", {}).get("applicant_type")
        in {ngo_org_type, "MIXED"}
    ]
    candidates = applicant_matches or variants

    ngo_country = ngo.get("country_of_registration")
    if ngo_country:
        geo_matches = [
            variant
            for variant in candidates
            if ngo_country
            in (variant.get("eligibility_rules", {}).get("geographies") or [])
        ]
        if geo_matches:
            warning = "VARIANT_SELECTION_AMBIGUOUS" if len(geo_matches) > 1 else None
            return geo_matches[0].get("variant_id"), warning

    warning = "VARIANT_SELECTION_AMBIGUOUS" if len(candidates) > 1 else None
    return candidates[0].get("variant_id"), warning


def _apply_opportunity_aliases(
    opportunity: dict[str, Any],
    derived: dict[str, Any],
    requirements: dict | None,
) -> None:
    opportunity["grant_amount"] = derived.get("grant_amount_display")
    opportunity["priorities"] = derived.get("opportunity_priorities_phrases") or []
    geographies: list[str] = []
    if requirements:
        for variant in requirements.get("variants") or []:
            geos = variant.get("eligibility_rules", {}).get("geographies") or []
            geographies.extend([geo for geo in geos if geo])
    if geographies:
        opportunity["target_regions"] = geographies
    else:
        opportunity["target_regions"] = opportunity.get("location_text")


def _format_number(value: Any) -> str:
    value = _coerce_number(value)
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    try:
        return f"{value:,.0f}"
    except Exception:
        return str(value)


def _coerce_number(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return None

