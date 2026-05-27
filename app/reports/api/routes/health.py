from fastapi import APIRouter

router = APIRouter(tags=["reports"])


@router.get("/api/reports/health")
def reports_health() -> dict:
    return {"status": "ok", "module": "reports"}
