from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.entitlements import router as entitlements_router
from app.api.routes.fit_scans import router as fit_scans_router
from app.api.routes.funding_opportunities import router as funding_opportunities_router
from app.api.routes.health import router as health_router
from app.api.routes.ngo_profile import router as ngo_profile_router
from app.api.routes.proposals import router as proposals_router
from app.core.config import get_settings, validate_config
from app.core.errors import DomainError

validate_config()
settings = get_settings()
cors_allow_origins = [
    origin.strip() for origin in settings.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()
]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(billing_router)
app.include_router(entitlements_router)
app.include_router(fit_scans_router)
app.include_router(funding_opportunities_router)
app.include_router(ngo_profile_router)
app.include_router(proposals_router)


def _build_standard_error_payload(
    request: Request,
    *,
    error_code: str,
    message: str,
    details: dict | None = None,
) -> dict:
    payload: dict = {"error_code": error_code, "message": message}
    if details is not None:
        payload["details"] = details
    request_id = request.headers.get("x-request-id")
    if request_id:
        payload["request_id"] = request_id
    return payload


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    payload = _build_standard_error_payload(
        request,
        error_code="VALIDATION_ERROR",
        message="Validation error",
        details={"errors": exc.errors()},
    )
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(StarletteHTTPException)
def http_exception_handler(request: Request, exc: StarletteHTTPException):
    status_code = exc.status_code
    error_code_by_status = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMITED",
        500: "INTERNAL_SERVER_ERROR",
    }
    error_code = error_code_by_status.get(status_code, "INTERNAL_SERVER_ERROR")
    default_message_by_status = {
        400: "Bad request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not found",
        409: "Conflict",
        422: "Validation error",
        429: "Too many requests",
        500: "Internal server error",
    }
    detail = exc.detail if isinstance(exc.detail, str) else None
    message = detail or default_message_by_status.get(status_code, "Request failed")
    if detail == "Not authenticated":
        message = "Unauthorized"
        error_code = "UNAUTHORIZED"
        status_code = 401
    payload = _build_standard_error_payload(
        request, error_code=error_code, message=message
    )
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(DomainError)
def domain_error_handler(request: Request, exc: DomainError):
    payload = _build_standard_error_payload(
        request, error_code=exc.error_code, message=exc.message, details=exc.details
    )
    request_id = request.headers.get("x-request-id")
    if request_id:
        import logging

        logging.getLogger("api").info(
            "domain_error code=%s request_id=%s", exc.error_code, request_id
        )
    status_code = exc.status_code
    if exc.error_code == "QUOTA_EXCEEDED":
        status_code = 429
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(Exception)
def unhandled_exception_handler(request: Request, exc: Exception):
    _ = exc
    payload = _build_standard_error_payload(
        request,
        error_code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
    )
    return JSONResponse(status_code=500, content=payload)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        routes=app.routes,
    )
    components = openapi_schema.setdefault("components", {})
    schemas = components.setdefault("schemas", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["HTTPBearer"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
    }
    schemas["StandardErrorResponse"] = {
        "type": "object",
        "properties": {
            "error_code": {"type": "string"},
            "message": {"type": "string"},
            "details": {"type": "object", "nullable": True},
            "request_id": {"type": "string", "nullable": True},
        },
        "required": ["error_code", "message"],
    }

    public_paths = {
        "/health",
        "/api/auth/google/start",
        "/api/auth/google/callback",
        "/api/auth/magic-link/request",
        "/api/auth/exchange",
        "/api/auth/magic-link/consume",
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/billing/webhook",
    }
    standard_error_ref = {"$ref": "#/components/schemas/StandardErrorResponse"}

    for path, methods in openapi_schema.get("paths", {}).items():
        for method, operation in methods.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            responses = operation.setdefault("responses", {})

            # Ensure 422 uses the standard error envelope rather than HTTPValidationError.
            responses["422"] = {
                "description": "Validation Error",
                "content": {"application/json": {"schema": standard_error_ref}},
            }

            if path.startswith("/api") and path not in public_paths:
                operation["security"] = [{"HTTPBearer": []}]
                for code, description in (
                    ("401", "Unauthorized"),
                    ("403", "Forbidden"),
                    ("404", "Not Found"),
                    ("429", "Too Many Requests"),
                    ("500", "Internal Server Error"),
                ):
                    response = responses.setdefault(code, {"description": description})
                    response["description"] = response.get("description") or description
                    content = response.setdefault("content", {})
                    app_json = content.setdefault("application/json", {})
                    app_json["schema"] = standard_error_ref
            else:
                operation.pop("security", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
