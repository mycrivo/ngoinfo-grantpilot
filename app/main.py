from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.entitlements import router as entitlements_router
from app.api.routes.fit_scans import router as fit_scans_router
from app.api.routes.health import router as health_router
from app.api.routes.ngo_profile import router as ngo_profile_router
from app.core.config import validate_config
from app.core.errors import DomainError

validate_config()

app = FastAPI()
app.include_router(health_router)
app.include_router(auth_router)
app.include_router(entitlements_router)
app.include_router(fit_scans_router)
app.include_router(ngo_profile_router)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("x-request-id")
    details = {"fields": [err.get("loc") for err in exc.errors()]}
    payload = {"error_code": "VALIDATION_ERROR", "message": "Validation error", "details": details}
    if request_id:
        payload["request_id"] = request_id
    return JSONResponse(status_code=422, content=payload)


@app.exception_handler(DomainError)
def domain_error_handler(request: Request, exc: DomainError):
    payload = {"error_code": exc.error_code, "message": exc.message}
    if exc.details:
        payload["details"] = exc.details
    request_id = request.headers.get("x-request-id")
    if request_id:
        payload["request_id"] = request_id
    if request_id:
        import logging

        logging.getLogger("api").info(
            "domain_error code=%s request_id=%s", exc.error_code, request_id
        )
    status_code = exc.status_code
    if exc.error_code == "QUOTA_EXCEEDED":
        status_code = 429
    return JSONResponse(status_code=status_code, content=payload)
