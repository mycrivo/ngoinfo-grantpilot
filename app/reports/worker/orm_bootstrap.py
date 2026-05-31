"""Register the full ORM model surface before worker DB access.

The web process loads ``app.models`` transitively via API routes; the worker
entrypoint must do so explicitly or SQLAlchemy cannot resolve cross-package
relationships (e.g. DonorReport → User) on the first query.
"""


def ensure_orm_models_registered() -> None:
    import app.models  # noqa: F401 — core ORM registry (User, Proposal, …)
    import app.reports.models  # noqa: F401 — M&E ORM registry
