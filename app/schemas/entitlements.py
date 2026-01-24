from pydantic import BaseModel


class PeriodInfo(BaseModel):
    type: str
    start_at: str | None
    end_at: str | None
    resets_at: str | None


class QuotaInfo(BaseModel):
    allowed: int
    used: int
    remaining: int


class EntitlementsResponse(BaseModel):
    plan: str
    period: PeriodInfo
    quotas: dict[str, QuotaInfo]
