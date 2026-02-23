from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.proposal import (
    ProposalCreateRequest,
    ProposalDetailResponse,
    ProposalExportRequest,
    ProposalListItem,
    ProposalListResponse,
    ProposalResponse,
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
        status=proposal.status,
        created_at=proposal.created_at,
        generation_summary=content_json.get("generation_summary"),
    )


def _to_detail_response(proposal) -> ProposalDetailResponse:
    return ProposalDetailResponse(
        id=proposal.id,
        funding_opportunity_id=proposal.funding_opportunity_id,
        status=proposal.status,
        version=proposal.version,
        regeneration_count=proposal.regeneration_count,
        content_json=proposal.content_json or {},
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
    )
