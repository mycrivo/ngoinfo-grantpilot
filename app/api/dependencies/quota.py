from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_user
from app.db.session import get_db
from app.services.quota_service import enforce_quota


def require_quota(event_type: str):
    def _guard(
        db: Session = Depends(get_db),
        current_user=Depends(get_current_user),
    ):
        enforce_quota(db, current_user.id, event_type)
        return current_user

    return _guard
