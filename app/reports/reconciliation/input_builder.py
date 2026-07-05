"""Assemble reconciliation inputs from uploaded_documents — no extractor calls."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from app.reports.extraction.docling_content_guard import UNREADABLE_DOCUMENT_LOW_CONTENT

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(text: str) -> str:
    """Lowercase, non-alphanumeric -> single underscore; stable namespace component."""
    slug = _SLUG_RE.sub("_", str(text or "").strip().lower()).strip("_")
    return slug or "unknown"


class FactCandidate(BaseModel):
    candidate_id: str
    document_id: str
    source_label: str
    classification: str
    field_path: str
    semantic_hint: str
    value_raw: str | None = None
    value_normalized: str | None = None
    unit: str | None = None
    multi_value: bool = False
    stated_values: list[dict[str, Any]] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    # Section-routing carrier (Package A): the source-declared section label for the
    # row this candidate came from. Set deterministically in the flattener; never
    # inferred. Carried to the KB fact via a cell_ref join in the reconciler.
    source_section: str | None = None


class UnreadableSourceInput(BaseModel):
    document_id: str
    source_label: str
    code: str
    message: str


class ReconciliationInputBundle(BaseModel):
    fact_candidates: list[FactCandidate] = Field(default_factory=list)
    unreadable_sources: list[UnreadableSourceInput] = Field(default_factory=list)


def _provenance_from_dict(prov: dict | None) -> dict[str, Any]:
    if not prov:
        return {"excerpt": "(no excerpt)"}
    out = {"excerpt": prov.get("excerpt") or "(no excerpt)"}
    for key in ("section_label", "page", "char_start", "char_end"):
        if prov.get(key) is not None:
            out[key] = prov[key]
    return out


def _locator_provenance(loc: dict | None, fallback: str) -> dict[str, Any]:
    if not loc:
        return {"excerpt": fallback, "cell_ref": None}
    sheet = loc.get("sheet", "")
    cell = loc.get("cell_range", "")
    return {"excerpt": fallback[:80], "cell_ref": f"{sheet}!{cell}" if sheet and cell else cell}


def _grant_term_field(
    *,
    doc_id: str,
    source_label: str,
    field_path: str,
    semantic_hint: str,
    field: dict,
) -> list[FactCandidate]:
    if field.get("absent"):
        return []
    cid_base = f"{doc_id}:{field_path}"
    if field.get("multi_value") and field.get("stated_values"):
        return [
            FactCandidate(
                candidate_id=f"{cid_base}:stated:{idx}",
                document_id=doc_id,
                source_label=source_label,
                classification="grant_letter",
                field_path=f"{field_path}.stated_values[{idx}]",
                semantic_hint=semantic_hint,
                value_raw=sv.get("raw"),
                value_normalized=sv.get("normalized"),
                multi_value=True,
                stated_values=field.get("stated_values") or [],
                provenance=_provenance_from_dict(sv.get("provenance")),
            )
            for idx, sv in enumerate(field["stated_values"])
        ]
    return [
        FactCandidate(
            candidate_id=cid_base,
            document_id=doc_id,
            source_label=source_label,
            classification="grant_letter",
            field_path=field_path,
            semantic_hint=semantic_hint,
            value_raw=field.get("raw"),
            value_normalized=field.get("normalized"),
            provenance=_provenance_from_dict(field.get("provenance")),
        )
    ]


def _flatten_grant_terms(
    doc_id: str, source_label: str, structured: dict
) -> list[FactCandidate]:
    out: list[FactCandidate] = []
    for name in ("funder", "grant_reference"):
        field = structured.get(name) or {}
        out.extend(
            _grant_term_field(
                doc_id=doc_id,
                source_label=source_label,
                field_path=name,
                semantic_hint=name.replace("_", " "),
                field=field,
            )
        )
    budget = structured.get("award_budget") or {}
    for sub in ("amount", "currency"):
        field = budget.get(sub) or {}
        hint = (
            "Total approved programme budget (contract)"
            if sub == "amount"
            else "Award budget currency"
        )
        out.extend(
            _grant_term_field(
                doc_id=doc_id,
                source_label=source_label,
                field_path=f"award_budget.{sub}",
                semantic_hint=hint,
                field=field,
            )
        )
    for period_name in ("grant_period", "reporting_period"):
        period = structured.get(period_name) or {}
        for side in ("start", "end"):
            field = period.get(side) or {}
            hint = f"{period_name} {side}"
            out.extend(
                _grant_term_field(
                    doc_id=doc_id,
                    source_label=source_label,
                    field_path=f"{period_name}.{side}",
                    semantic_hint=hint,
                    field=field,
                )
            )
    for idx, obligation in enumerate(structured.get("reporting_obligations") or []):
        out.append(
            FactCandidate(
                candidate_id=f"{doc_id}:reporting_obligations[{idx}]",
                document_id=doc_id,
                source_label=source_label,
                classification="grant_letter",
                field_path=f"reporting_obligations[{idx}]",
                semantic_hint=obligation.get("report_type", "reporting obligation"),
                value_raw=obligation.get("raw"),
                value_normalized=obligation.get("report_type"),
                provenance=_provenance_from_dict(obligation.get("provenance")),
            )
        )
    for idx, deadline in enumerate(structured.get("reporting_deadlines") or []):
        out.extend(
            _grant_term_field(
                doc_id=doc_id,
                source_label=source_label,
                field_path=f"reporting_deadlines[{idx}]",
                semantic_hint="reporting deadline",
                field=deadline,
            )
        )
    return out


def _flatten_proposal(doc_id: str, source_label: str, structured: dict) -> list[FactCandidate]:
    out: list[FactCandidate] = []
    for obj in structured.get("objectives") or []:
        if obj.get("status") != "extracted":
            continue
        out.append(
            FactCandidate(
                candidate_id=f"{doc_id}:objectives:{obj['objective_key']}",
                document_id=doc_id,
                source_label=source_label,
                classification="proposal",
                field_path=f"objectives.{obj['objective_key']}",
                semantic_hint=f"Objective ({obj.get('level')})",
                value_raw=obj.get("label"),
                value_normalized=obj.get("label"),
                provenance=_provenance_from_dict(obj.get("provenance")),
            )
        )
    for ind in structured.get("indicators") or []:
        if ind.get("status") != "extracted":
            continue
        target = ind.get("target") or {}
        out.append(
            FactCandidate(
                candidate_id=f"{doc_id}:indicators:{ind['indicator_key']}:target",
                document_id=doc_id,
                source_label=source_label,
                classification="proposal",
                field_path=f"indicators.{ind['indicator_key']}.target",
                semantic_hint=f"Proposal indicator target ({ind.get('indicator_key')})",
                value_raw=str(target.get("value")) if target.get("value") is not None else None,
                value_normalized=(
                    str(target.get("value")) if target.get("value") is not None else None
                ),
                provenance=_provenance_from_dict(ind.get("provenance")),
            )
        )
    # Package B: promote named partners and the community-consultation narrative into
    # the partnerships.* / engagement.* namespaces merged-A routes to the
    # community-involvement section. Promotion only — every value is what the proposal
    # states; nothing inferred. No source_section: these route by declared namespace.
    for partner in structured.get("partners") or []:
        if partner.get("status") != "extracted":
            continue
        name = partner.get("name")
        if not name:
            continue
        out.append(
            FactCandidate(
                candidate_id=f"{doc_id}:partnerships:{partner.get('partner_key') or _slug(name)}",
                document_id=doc_id,
                source_label=source_label,
                classification="proposal",
                field_path=f"partnerships.{_slug(name)}",
                semantic_hint="Named partner / collaborator",
                value_raw=name,
                value_normalized=name,
                provenance=_provenance_from_dict(partner.get("provenance")),
            )
        )
    for eng in structured.get("consultation") or []:
        if eng.get("status") != "extracted":
            continue
        key = eng.get("engagement_key")
        label = eng.get("label")
        if not key and not label:
            continue
        value = eng.get("value")
        out.append(
            FactCandidate(
                candidate_id=f"{doc_id}:engagement:{key or _slug(label)}",
                document_id=doc_id,
                source_label=source_label,
                classification="proposal",
                field_path=f"engagement.{_slug(key or label)}",
                semantic_hint="Community consultation / involvement",
                value_raw=(str(value) if value is not None else label),
                value_normalized=(str(value) if value is not None else label),
                unit=eng.get("unit"),
                provenance=_provenance_from_dict(eng.get("provenance")),
            )
        )
    return out


def _tabular_field_candidate(
    *,
    doc_id: str,
    source_label: str,
    field_path: str,
    semantic_hint: str,
    field: dict,
) -> FactCandidate | None:
    if field.get("absent"):
        return None
    loc = field.get("source_locator")
    return FactCandidate(
        candidate_id=f"{doc_id}:{field_path}",
        document_id=doc_id,
        source_label=source_label,
        classification="indicator_data",
        field_path=field_path,
        semantic_hint=semantic_hint,
        value_raw=field.get("raw"),
        value_normalized=field.get("normalized"),
        provenance=_locator_provenance(loc, field.get("raw") or semantic_hint),
    )


def _flatten_indicator_data(
    doc_id: str, source_label: str, structured: dict
) -> list[FactCandidate]:
    out: list[FactCandidate] = []
    for row in structured.get("indicators") or []:
        row_id = row.get("row_id", "unknown")
        # Package A: carry the source-declared section label (captured deterministically
        # at extraction) onto every fact candidate from this row, for section routing.
        section_field = row.get("section_assignment") or {}
        source_section = section_field.get("raw") if isinstance(section_field, dict) else None
        for facet, hint in (
            ("target", "indicator target"),
            ("actual", "indicator actual"),
        ):
            field = row.get(facet) or {}
            cand = _tabular_field_candidate(
                doc_id=doc_id,
                source_label=source_label,
                field_path=f"indicators.{row_id}.{facet}",
                semantic_hint=f"{hint} ({row_id})",
                field=field,
            )
            if cand:
                cand.source_section = source_section
                out.append(cand)
        # Package C: promote per-band demographic disaggregation (age/gender/etc.)
        # into source-located candidates. Promotion only — every value traces to its
        # own source cell, only bands present in the source appear, nothing inferred.
        # stated_total is intentionally NOT promoted (it duplicates the row actual).
        name_field = row.get("indicator_name") or {}
        indicator_name = (
            name_field.get("raw") if isinstance(name_field, dict) else None
        ) or str(row_id)
        for dimension in row.get("disaggregation") or []:
            if not isinstance(dimension, dict):
                continue
            dim_name = str(dimension.get("dimension") or "breakdown")
            dim_slug = _slug(dim_name)
            for band in dimension.get("breakdown") or []:
                if not isinstance(band, dict):
                    continue
                band_label = str(band.get("label") or "")
                value_field = band.get("value") or {}
                if not isinstance(value_field, dict) or value_field.get("absent"):
                    continue
                cand = _tabular_field_candidate(
                    doc_id=doc_id,
                    source_label=source_label,
                    field_path=(
                        f"indicators.{row_id}.disaggregation."
                        f"{dim_slug}.{_slug(band_label)}"
                    ),
                    semantic_hint=f"{indicator_name} - {dim_name} - {band_label}",
                    field=value_field,
                )
                if cand:
                    cand.source_section = source_section
                    out.append(cand)
        # Package B: promote the row's evidence/note/change cell into a fact that
        # merged-A routes to changes_and_next_steps via the declared indicators.*.note
        # namespace. DELIBERATELY no source_section: a note inheriting the row's section
        # (e.g. "Difference made" / "Spend summary") would be source-pinned there and
        # stranded away from changes. The note cell_ref still lives in provenance.
        note_field = row.get("note") or {}
        if isinstance(note_field, dict) and not note_field.get("absent"):
            note_cand = _tabular_field_candidate(
                doc_id=doc_id,
                source_label=source_label,
                field_path=f"indicators.{row_id}.note",
                semantic_hint=f"Evidence / delivery note ({row_id})",
                field=note_field,
            )
            if note_cand:
                out.append(note_cand)
    financials = structured.get("financials") or {}
    currency = financials.get("currency") or {}
    if not currency.get("absent"):
        cand = _tabular_field_candidate(
            doc_id=doc_id,
            source_label=source_label,
            field_path="financials.currency",
            semantic_hint="Financials currency",
            field=currency,
        )
        if cand:
            out.append(cand)
    for line in financials.get("lines") or []:
        line_key = line.get("line_key", "line")
        label_field = line.get("label") or {}
        label_raw = label_field.get("raw") or line_key
        for facet, hint in (("budget", "budget"), ("actual", "actual spend")):
            field = line.get(facet) or {}
            semantic = f"{label_raw} — {hint}"
            cand = _tabular_field_candidate(
                doc_id=doc_id,
                source_label=source_label,
                field_path=f"financials.lines.{line_key}.{facet}",
                semantic_hint=semantic,
                field=field,
            )
            if cand:
                out.append(cand)
    return out


def _is_unreadable_extraction(extracted_json: dict) -> bool:
    structured = extracted_json.get("structured") or {}
    if structured.get("extraction_outcome") == "unreadable":
        return True
    if extracted_json.get("error") == UNREADABLE_DOCUMENT_LOW_CONTENT:
        return True
    return False


def _degraded_source_from_extracted_json(
    doc_id: str,
    source_label: str,
    extracted_json: dict,
) -> UnreadableSourceInput:
    structured = extracted_json.get("structured") or {}
    code = (
        extracted_json.get("error")
        or structured.get("degraded_code")
        or "DEGRADED_EXTRACTION"
    )
    message = extracted_json.get("error") or "Could not extract usable data from this upload."
    return UnreadableSourceInput(
        document_id=doc_id,
        source_label=source_label,
        code=str(code),
        message=str(message),
    )


def document_dict_to_input(doc: dict[str, Any]) -> ReconciliationInputBundle:
    """Build candidates from a fixture manifest document entry."""
    doc_id = str(doc["id"])
    source_label = doc.get("original_filename") or doc_id
    classification = doc.get("classification") or "other"
    extracted_path = doc.get("extracted_json_path")
    if extracted_path:
        extracted_json = json.loads(Path(extracted_path).read_text(encoding="utf-8"))
    else:
        extracted_json = doc.get("extracted_json") or {}

    if _is_unreadable_extraction(extracted_json):
        return ReconciliationInputBundle(
            unreadable_sources=[
                UnreadableSourceInput(
                    document_id=doc_id,
                    source_label=source_label,
                    code=UNREADABLE_DOCUMENT_LOW_CONTENT,
                    message=extracted_json.get("error")
                    or "Could not extract usable text from this upload.",
                )
            ]
        )

    structured = extracted_json.get("structured") or {}
    if structured.get("extraction_outcome") == "degraded":
        return ReconciliationInputBundle(
            unreadable_sources=[
                _degraded_source_from_extracted_json(doc_id, source_label, extracted_json)
            ]
        )
    if structured.get("extraction_outcome") in ("failed", "unreadable"):
        return ReconciliationInputBundle()

    candidates: list[FactCandidate] = []
    if classification in ("grant_letter", "mou"):
        candidates = _flatten_grant_terms(doc_id, source_label, structured)
    elif classification == "proposal":
        candidates = _flatten_proposal(doc_id, source_label, structured)
    elif classification == "indicator_data":
        candidates = _flatten_indicator_data(doc_id, source_label, structured)

    return ReconciliationInputBundle(fact_candidates=candidates)


def _dedupe_unreadable_sources(
    sources: list,
) -> list:
    """Keep first unreadable entry per document_id."""
    seen: set[str] = set()
    deduped = []
    for item in sources:
        doc_id = getattr(item, "document_id", None) or (
            item.get("document_id") if isinstance(item, dict) else None
        )
        if doc_id is None:
            deduped.append(item)
            continue
        key = str(doc_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def build_reconciliation_bundle(documents: list[Any]) -> ReconciliationInputBundle:
    """Merge bundle from ORM UploadedDocument rows or dict fixtures."""
    merged_candidates: list[FactCandidate] = []
    merged_unreadable: list[UnreadableSourceInput] = []
    for doc in documents:
        if hasattr(doc, "id"):
            entry = {
                "id": str(doc.id),
                "original_filename": doc.original_filename,
                "classification": doc.classification,
                "extracted_json": doc.extracted_json or {},
            }
        else:
            entry = doc
        partial = document_dict_to_input(entry)
        merged_candidates.extend(partial.fact_candidates)
        merged_unreadable.extend(partial.unreadable_sources)
    merged_unreadable = _dedupe_unreadable_sources(merged_unreadable)
    return ReconciliationInputBundle(
        fact_candidates=merged_candidates,
        unreadable_sources=merged_unreadable,
    )


def build_reconciliation_bundle_from_fixture(manifest_path: Path) -> ReconciliationInputBundle:
    """Load tests/fixtures/reconciler manifest and resolve extracted_json paths."""
    root = manifest_path.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    docs = []
    for doc in manifest.get("documents") or []:
        doc = dict(doc)
        rel = doc.get("extracted_json_path")
        if rel:
            doc["extracted_json_path"] = str((root / rel).resolve())
        docs.append(doc)
    return build_reconciliation_bundle(docs)
