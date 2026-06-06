from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.models.funding_opportunity import FundingOpportunity
from app.models.ngo_profile import NGOProfile
from app.models.usage_ledger import UsageActionType
from app.services.proposal_docx_renderer import build_proposal_docx_bytes
from app.services.proposal_service import ProposalService
from app.services.quota_service import record_usage


class ExportService:
    def __init__(self, db_session: Session) -> None:
        self.db = db_session
        self.proposals = ProposalService(db_session)

    def export_docx(self, *, user, proposal_id: UUID, export_format: str) -> tuple[bytes, str]:
        normalized_format = (export_format or "").strip().upper()
        if normalized_format != "DOCX":
            raise DomainError(
                error_code="UNSUPPORTED_FORMAT",
                message="Only DOCX export is supported.",
                status_code=422,
            )

        proposal = self.proposals.get_proposal(user=user, proposal_id=proposal_id)
        opportunity = self.db.get(FundingOpportunity, proposal.funding_opportunity_id)
        profile = self.db.query(NGOProfile).filter(NGOProfile.user_id == user.id).one_or_none()

        opportunity_title = opportunity.title if opportunity else "Untitled Opportunity"
        ngo_name = profile.organization_name if profile else user.email
        generated_at = datetime.now(timezone.utc)
        docx_bytes = build_proposal_docx_bytes(
            content_json=proposal.content_json or {},
            opportunity_title=opportunity_title,
            ngo_name=ngo_name,
            generated_at=generated_at,
        )

        idempotency_key = (
            f"docx_export:{user.id}:{proposal.id}:v{int(proposal.version)}"
        )
        record_usage(
            self.db,
            user.id,
            UsageActionType.DOCX_EXPORT.value,
            idempotency_key=idempotency_key,
            commit=True,
        )

        filename = f"proposal-{proposal.id}.docx"
        return docx_bytes, filename

