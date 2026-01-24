import uuid

import jwt
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import DomainError
from app.db.session import get_db
from app.models.user import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.lower().startswith("bearer "):
        raise DomainError(
            error_code="AUTH_REQUIRED",
            message="Authentication required",
            status_code=401,
        )

    token = auth_header.split(" ", 1)[1].strip()
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_JWT_SIGNING_KEY,
            algorithms=["HS256"],
            audience="grantpilot-web",
            issuer="grantpilot",
        )
    except Exception:
        raise DomainError(
            error_code="AUTH_INVALID",
            message="Invalid authentication token",
            status_code=401,
        )

    user_id = payload.get("sub")
    if not user_id:
        raise DomainError(
            error_code="AUTH_INVALID",
            message="Invalid authentication token",
            status_code=401,
        )

    try:
        user_uuid = uuid.UUID(str(user_id))
    except ValueError:
        raise DomainError(
            error_code="AUTH_INVALID",
            message="Invalid authentication token",
            status_code=401,
        )

    user = db.get(User, user_uuid)
    if not user:
        raise DomainError(
            error_code="AUTH_INVALID",
            message="Invalid authentication token",
            status_code=401,
        )
    return user
