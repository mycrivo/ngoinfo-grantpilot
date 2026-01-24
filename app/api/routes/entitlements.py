from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.schemas.entitlements import EntitlementsResponse
from app.services.quota_service import get_entitlements

router = APIRouter(prefix="/api", tags=["entitlements"])


@router.get("/me/entitlements", response_model=EntitlementsResponse)
def get_entitlements(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return get_entitlements(db, current_user.id)
