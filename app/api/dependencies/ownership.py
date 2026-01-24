from app.core.errors import ForbiddenError


def require_profile_owner(current_user_id: str, owner_user_id: str) -> None:
    if str(current_user_id) != str(owner_user_id):
        raise ForbiddenError(
            error_code="FORBIDDEN",
            message="Forbidden",
            status_code=403,
        )
