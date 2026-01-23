from datetime import datetime, timezone
import os

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "service": os.getenv("APP_NAME", "grantpilot-backend"),
        "version": os.getenv("PROMPT_VERSION") or "unknown",
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }
