from pydantic import BaseModel


class EntitlementQuota(BaseModel):
    limit: int
    used: int
    remaining: int
    period: str
    reset_at: str | None


class ProposalRegenerationEntitlement(BaseModel):
    limit_per_proposal: int


class EntitlementsPayload(BaseModel):
    fit_scans: EntitlementQuota
    proposals: EntitlementQuota
    proposal_regenerations: ProposalRegenerationEntitlement


class EntitlementsResponse(BaseModel):
    plan: str
    entitlements: EntitlementsPayload
