# Taxonomy Audit (Post C-02)

Status: **Audit Record**  
Date: **2026-02-04**  
Scope: **Error taxonomy + HTTP status code compliance**  
References: `API_CONTRACT.md`, `mvp_execution_plan_FINAL_2.md`, `GUARDRAILS_RUNTIME_AND_SECURITY.md`, `REPO_STRUCTURE_AND_SERVICE_PATTERNS.md`

---

## 1) Global Error Envelope + Handler Behavior

**Handlers (evidence):**
```32:59:app/main.py
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
```

**Status code rule:** `DomainError.status_code` is used, except `QUOTA_EXCEEDED` is forced to 429 in the handler.

---

## 2) Domain Error Taxonomy Definition

**Definitions (evidence):**
```4:27:app/core/errors.py
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

class InvalidActionTypeError(ValueError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
```

**Canonical mapping exists:** **No** — status correctness depends on raise-sites.

---

## 3) Raise-Site Inventory (AI + Fit Scan + Quota)

| file | exception class | error_code | status_code | endpoint(s) |
|---|---|---|---|---|
| `app/ai/fit_scan_executor.py` | DomainError | `FIT_SCAN_FAILED` | 500 | `POST /api/fit-scans` |
| `app/services/fit_scan_service.py` | NotFoundError | `OPPORTUNITY_NOT_FOUND` | 404 | `POST /api/fit-scans` |
| `app/services/fit_scan_service.py` | ConflictError | `PROFILE_INCOMPLETE` | 409 | `POST /api/fit-scans` |
| `app/services/fit_scan_service.py` | DomainError | `FIT_SCAN_FAILED` | 500 | `POST /api/fit-scans` |
| `app/services/fit_scan_service.py` | NotFoundError | `FIT_SCAN_NOT_FOUND` | 404 | `GET /api/fit-scans/{id}` |
| `app/services/fit_scan_service.py` | ForbiddenError | `FORBIDDEN` | 403 | `GET /api/fit-scans/{id}` |
| `app/services/quota_service.py` | ForbiddenError | `QUOTA_EXCEEDED` | 403 → forced to 429 | `POST /api/fit-scans` |

---

## 4) Contract Comparison (Fit Scan)

**API_CONTRACT allowed error codes (Fit Scan):**
- 401 UNAUTHORIZED
- 403 FORBIDDEN
- 404 OPPORTUNITY_NOT_FOUND
- 409 PROFILE_INCOMPLETE (details.missing_fields[] required)
- 429 QUOTA_EXCEEDED
- 500 FIT_SCAN_FAILED

**Result:** PASS — all observed error codes and statuses align.

---

## 5) Guardrails Compliance

### Rule 2 — Wrap AI errors in DomainError

**Evidence:**
```200:224:app/ai/fit_scan_executor.py
try:
    response = self._client.create_chat_completion(...)
except OpenAIServiceError as exc:
    raise DomainError(
        error_code="FIT_SCAN_FAILED",
        message="AI service unavailable",
        status_code=500,
        details={"reason": exc.category, "retry_attempted": exc.retry_attempted},
    ) from exc
```

### Rule 5 — No secrets in logs/responses

**Evidence (OpenAI logging):**
```93:100:app/integrations/openai_client.py
logger.info(
    "openai_call_success feature=%s user_id=%s latency_ms=%s attempts=%s",
    feature,
    user_id or "unknown",
    latency_ms,
    attempt + 1,
)

118:127:app/integrations/openai_client.py
logger.warning(
    "openai_call_error feature=%s user_id=%s category=%s retryable=%s "
    "attempt=%s latency_ms=%s",
    feature,
    user_id or "unknown",
    last_error.category if last_error else "unknown",
    retryable,
    attempt + 1,
    latency_ms,
)
```

**Result:** PASS — no tokens, headers, API keys, or raw prompt bodies logged.

---

## 6) Response Shape Verification (Fit Scan)

**Success envelope:**
```18:28:app/api/routes/fit_scans.py
@router.post("/fit-scans", response_model=FitScanResponseEnvelope)
def create_fit_scan(...):
    service = FitScanService(db)
    fit_scan = service.run_fit_scan(...)
    return FitScanResponseEnvelope(fit_scan=_to_response(fit_scan))
```

**Error envelope:** provided by `DomainError` handler in `app/main.py` (see section 1).

---

## Verdict

**Taxonomy compliance: PASS** (Post C-02)
