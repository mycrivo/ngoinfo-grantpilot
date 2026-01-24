import json
from typing import Any

from app.core.errors import DomainError


def validate_deadline(deadline_type: str, application_deadline: Any | None) -> None:
    if deadline_type == "FIXED" and application_deadline is None:
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="application_deadline is required when deadline_type is FIXED",
            status_code=422,
        )


def validate_requirements_json(requirements_json: Any) -> None:
    if requirements_json is None:
        raise DomainError(
            error_code="VALIDATION_ERROR",
            message="requirements_json is required",
            status_code=422,
        )
    if isinstance(requirements_json, (dict, list)):
        return
    if isinstance(requirements_json, str):
        try:
            json.loads(requirements_json)
        except json.JSONDecodeError as exc:
            raise DomainError(
                error_code="VALIDATION_ERROR",
                message="requirements_json must be valid JSON",
                status_code=422,
                details={"error": str(exc)},
            )
        return
    raise DomainError(
        error_code="VALIDATION_ERROR",
        message="requirements_json must be valid JSON",
        status_code=422,
    )
