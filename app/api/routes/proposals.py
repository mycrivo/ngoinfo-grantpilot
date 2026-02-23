from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.proposal import (
    ProposalContentJson,
    ProposalCreateRequest,
    ProposalDetailResponse,
    ProposalExportRequest,
    ProposalGenerationSummary,
    ProposalListItem,
    ProposalListResponse,
    ProposalResponse,
    ProposalSection,
    ProposalSectionConstraints,
    ProposalSectionContent,
    StandardErrorResponse,
)
from app.services.export_service import ExportService
from app.services.proposal_service import ProposalService

router = APIRouter(prefix="/api", tags=["proposals"])


@router.post("/proposals", response_model=ProposalResponse)
def create_proposal(
    payload: ProposalCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ProposalService(db)
    proposal = service.create_proposal(user=current_user, payload=payload)
    return _to_summary_response(proposal)


@router.get(
    "/proposals",
    response_model=ProposalListResponse,
    responses={
        401: {"model": StandardErrorResponse},
        403: {"model": StandardErrorResponse},
        422: {"model": StandardErrorResponse},
        500: {"model": StandardErrorResponse},
    },
)
def list_proposals(
    limit: int = Query(default=5, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ProposalService(db)
    proposals = service.list_proposals(user=current_user, limit=limit)
    return ProposalListResponse(
        proposals=[
            ProposalListItem(
                id=proposal.id,
                funding_opportunity_id=proposal.funding_opportunity_id,
                fit_scan_id=proposal.fit_scan_id,
                opportunity_title=(
                    proposal.funding_opportunity.title
                    if proposal.funding_opportunity is not None
                    else None
                ),
                status=proposal.status,
                version=proposal.version,
                created_at=proposal.created_at,
                updated_at=proposal.updated_at,
                generation_summary=(proposal.content_json or {}).get("generation_summary"),
            )
            for proposal in proposals
        ]
    )


@router.get("/proposals/{proposal_id}", response_model=ProposalDetailResponse)
def get_proposal(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ProposalService(db)
    proposal = service.get_proposal(user=current_user, proposal_id=proposal_id)
    return _to_detail_response(proposal)


@router.post("/proposals/{proposal_id}/regenerate", response_model=ProposalDetailResponse)
def regenerate_proposal(
    proposal_id: UUID,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ProposalService(db)
    proposal = service.regenerate_proposal(user=current_user, proposal_id=proposal_id)
    return _to_detail_response(proposal)


@router.post("/proposals/{proposal_id}/export")
def export_proposal(
    proposal_id: UUID,
    payload: ProposalExportRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = ExportService(db)
    content, filename = service.export_docx(
        user=current_user,
        proposal_id=proposal_id,
        export_format=payload.format,
    )
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _to_summary_response(proposal) -> ProposalResponse:
    content_json = proposal.content_json or {}
    return ProposalResponse(
        id=proposal.id,
        funding_opportunity_id=proposal.funding_opportunity_id,
        fit_scan_id=proposal.fit_scan_id,
        opportunity_title=(
            proposal.funding_opportunity.title
            if proposal.funding_opportunity is not None
            else None
        ),
        status=proposal.status,
        version=proposal.version,
        created_at=proposal.created_at,
        generation_summary=_to_generation_summary(content_json.get("generation_summary")),
    )


def _to_detail_response(proposal) -> ProposalDetailResponse:
    return ProposalDetailResponse(
        id=proposal.id,
        funding_opportunity_id=proposal.funding_opportunity_id,
        fit_scan_id=proposal.fit_scan_id,
        opportunity_title=(
            proposal.funding_opportunity.title
            if proposal.funding_opportunity is not None
            else None
        ),
        status=proposal.status,
        version=proposal.version,
        regeneration_count=proposal.regeneration_count,
        content_json=_to_content_json(proposal.content_json),
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )


def _to_generation_summary(raw_summary) -> ProposalGenerationSummary | None:
    if not isinstance(raw_summary, dict):
        return None
    return ProposalGenerationSummary(
        total_items=int(raw_summary.get("total_items") or 0),
        generated=int(raw_summary.get("generated") or 0),
        failed=int(raw_summary.get("failed") or 0),
        manual_required=int(raw_summary.get("manual_required") or 0),
        warnings=[
            str(warning)
            for warning in (raw_summary.get("warnings") or [])
            if warning is not None
        ],
    )


def _to_content_json(raw_content) -> ProposalContentJson:
    content = raw_content if isinstance(raw_content, dict) else {}
    raw_sections = content.get("sections") if isinstance(content.get("sections"), list) else []
    sections = []
    for section in raw_sections:
        if not isinstance(section, dict):
            continue

        raw_generation_status = str(section.get("generation_status") or "MANUAL_REQUIRED")
        generation_status = (
            raw_generation_status
            if raw_generation_status in {"GENERATED", "FAILED", "MANUAL_REQUIRED"}
            else "MANUAL_REQUIRED"
        )

        raw_content_block = section.get("content")
        content_block = raw_content_block if isinstance(raw_content_block, dict) else {}

        raw_constraints = section.get("constraints_applied")
        constraints = raw_constraints if isinstance(raw_constraints, dict) else {}

        sections.append(
            ProposalSection(
                submission_item_id=(
                    str(section.get("submission_item_id"))
                    if section.get("submission_item_id") is not None
                    else None
                ),
                label=str(section.get("label") or ""),
                generation_status=generation_status,
                archetype=(
                    str(section.get("archetype"))
                    if section.get("archetype") is not None
                    else None
                ),
                content=ProposalSectionContent(
                    text=str(content_block.get("text") or ""),
                    assumptions=[
                        str(assumption)
                        for assumption in (content_block.get("assumptions") or [])
                        if assumption is not None
                    ],
                    evidence_used=[
                        str(evidence)
                        for evidence in (content_block.get("evidence_used") or [])
                        if evidence is not None
                    ],
                ),
                failure_reason=(
                    str(section.get("failure_reason"))
                    if section.get("failure_reason") is not None
                    else None
                ),
                constraints_applied=ProposalSectionConstraints(
                    word_limit=int(constraints.get("word_limit") or 0),
                    word_limit_respected=bool(
                        constraints.get("word_limit_respected", True)
                    ),
                ),
            )
        )

    summary = _to_generation_summary(content.get("generation_summary"))
    if summary is None:
        summary = ProposalGenerationSummary(
            total_items=0,
            generated=0,
            failed=0,
            manual_required=0,
            warnings=[],
        )

    return ProposalContentJson(sections=sections, generation_summary=summary)
