from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.proposal import (
    ProposalCreateRequest,
    ProposalDetailResponse,
    ProposalResponse,
)
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
