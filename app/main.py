from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.core.config import validate_config

validate_config()

app = FastAPI()
app.include_router(health_router)
app.include_router(auth_router)


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("x-request-id")
    details = {"fields": [err.get("loc") for err in exc.errors()]}
    payload = {"error_code": "VALIDATION_ERROR", "message": "Validation error", "details": details}
    if request_id:
        payload["request_id"] = request_id
    return JSONResponse(status_code=422, content=payload)
