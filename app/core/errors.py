from dataclasses import dataclass


@dataclass
class DomainError(Exception):
    error_code: str
    message: str
    status_code: int
    details: dict | None = None


class NotFoundError(DomainError):
    pass


class ConflictError(DomainError):
    pass


class ForbiddenError(DomainError):
    pass
