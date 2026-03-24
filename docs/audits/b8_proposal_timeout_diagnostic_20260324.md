# B8 Proposal Timeout Diagnostic (Read-Only)

Date: 2026-03-24  
Scope: Diagnostic data collection only for `POST /api/proposals` timeout and `PROPOSAL_GENERATION_FAILED`.

---

## 1) OpenAI Client Timeout Configuration

### Findings
- Client-level timeout is `30.0` seconds.
- No per-request timeout override is set on OpenAI `post()` calls.
- Retry is enabled with `_MAX_RETRIES = 1` (2 total attempts).
- Backoff is exponential with base `0.6s` plus jitter.

### Code Evidence
```python
# app/integrations/openai_client.py
_MAX_RETRIES = 1
_RETRY_BASE_DELAY_SECONDS = 0.6
...
self._client = httpx.Client(timeout=30.0)
...
max_attempts = _MAX_RETRIES + 1
...
resp = self._client.post(..., json=payload)
...
delay = _RETRY_BASE_DELAY_SECONDS * (2**attempt) + random.uniform(0, 0.2)
```

---

## 2) Model Used for GP-P02

### Findings
- GP-P02 uses env-driven model selection:
  - `OPENAI_MODEL_PRIMARY`
  - `OPENAI_MODEL_FALLBACK`
- Defaults are:
  - primary: `gpt-5.4`
  - fallback: `gpt-5.4-mini`
- Fit scan and proposal calls use the same model source.

### Code Evidence
```python
# app/core/config.py
OPENAI_MODEL_PRIMARY: str = "gpt-5.4"
OPENAI_MODEL_FALLBACK: str = "gpt-5.4-mini"
```

```python
# app/ai/prompt_runner.py (GP-P02 path)
response = client.create_chat_completion(
    model=settings.OPENAI_MODEL_PRIMARY,
    fallback_model=settings.OPENAI_MODEL_FALLBACK,
    ...
)
```

```python
# app/ai/fit_scan_executor.py (GP-F02 path)
response = self._client.create_chat_completion(
    model=settings.OPENAI_MODEL_PRIMARY,
    fallback_model=settings.OPENAI_MODEL_FALLBACK,
    ...
)
```

---

## 3) `max_completion_tokens` / `max_tokens` for GP-P02

### Findings
- GP-P02 prompt config uses `max_tokens = 2500`.
- `run_prompt()` passes `max_tokens` through to OpenAI client.
- OpenAI client sends `max_completion_tokens` first, and only falls back to `max_tokens` if OpenAI returns `400 unsupported_parameter` for that param.

### Code Evidence
```python
# app/ai/prompt_runner.py
"GP-P02": {
    ...
    "max_tokens": 2500,
}
...
response = client.create_chat_completion(..., max_tokens=max_tokens, feature=prompt_id)
```

```python
# app/integrations/openai_client.py
token_param = "max_completion_tokens"
payload = {..., token_param: max_tokens}
...
if _is_token_param_unsupported(...):
    token_param = "max_tokens"
    payload[token_param] = max_tokens
```

---

## 4) Prompt Payload Size Behavior

### Findings
- Full `prompt_inputs` JSON is serialized and embedded in every GP-P02 per-section call.
- `_generate_sections()` loops submission items and calls `_generate_item()` for each.
- No truncation or payload trimming logic exists in proposal generation path.
- GP-P02 user template length (before substitution): `2151` chars.

### Code Evidence
```python
# app/services/proposal_service.py
for item in submission_items:
    ...
    result = self._generate_item(
        prompt_inputs=prompt_inputs,
        fit_scan_output=fit_scan_output,
        submission_item=item,
    )
```

```python
# app/services/proposal_service.py
prompt_inputs_json = json.dumps(prompt_inputs, separators=(",", ":"), ensure_ascii=True)
user_prompt = GP_P02_USER_PROMPT_TEMPLATE
user_prompt = user_prompt.replace("{prompt_inputs_json}", prompt_inputs_json)
user_prompt = user_prompt.replace("{fit_scan_output_json}", fit_scan_output_json)
user_prompt = user_prompt.replace("{submission_item_json}", submission_item_json)
```

```python
# app/ai/prompts/proposal.py
GP_P02_USER_PROMPT_TEMPLATE = """..."""
```

Measured in diagnostics:
```text
len(GP_P02_USER_PROMPT_TEMPLATE) = 2151
```

---

## 5) Generatable Items for Opportunity `29dfccb1-ca58-4481-bfde-33e934a39039`

### Findings
From DB-level inspection (`FundingOpportunity.requirements_json`):
- Total variants: `2`
- Variant IDs:
  - `moes_track`
  - `icssr_track`
- Each variant submission items: `6`
- `generation_allowed=true` items per variant: `3`
- Generatable labels:
  - `Research Plan`
  - `Budget and Justification`
  - `Data Management Plan (Draft)`

Selection behavior when `selected_variant_id = null`:
- Uses deterministic selector.
- For NGO with `country_of_registration=Kenya`, selector resolved to `moes_track` with warning `VARIANT_SELECTION_AMBIGUOUS`.

### Code Evidence
```python
# app/ai/prompt_inputs_builder.py
selected_variant_id, _ = select_variant_deterministic(requirements, ngo, user)
...
def select_variant_deterministic(...):
    ...
    user_selected = user.get("selected_variant_id")
    if user_selected and any(...):
        return user_selected, None
    ...
    candidates = applicant_matches or variants
    ...
    return candidates[0].get("variant_id"), warning
```

---

## 6) Uvicorn / Railway Request Timeout

### Findings
- No explicit uvicorn request timeout flags found in startup.
- No `railway.json` or `railway.toml` in repo.
- No explicit app-level timeout middleware found.

### Code Evidence
```text
# Procfile
web: bash scripts/start.sh
```

```bash
# scripts/start.sh
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
```

No explicit `--timeout`, `--timeout-keep-alive`, or timeout middleware detected in code search.

---

## 7) Route-Level Timeout or Background Task Usage

### Findings
- `POST /api/proposals` is synchronous.
- No `BackgroundTasks`, no `asyncio.wait_for`, no route-level timeout wrapper.
- Execution path:
  1. `app/api/routes/proposals.py::create_proposal`
  2. `ProposalService.create_proposal`
  3. `_generate_sections`
  4. `_generate_item` (per section)
  5. `run_prompt`
  6. `OpenAIClient.create_chat_completion`
  7. Response returned after generation completes

### Code Evidence
```python
# app/api/routes/proposals.py
@router.post("/proposals", response_model=ProposalResponse)
def create_proposal(...):
    service = ProposalService(db)
    proposal = service.create_proposal(user=current_user, payload=payload)
    return _to_summary_response(proposal)
```

```python
# app/services/proposal_service.py
sections, summary = self._generate_sections(...)
...
result = self._generate_item(...)
...
return run_prompt(...)
```

```python
# app/ai/prompt_runner.py
response = client.create_chat_completion(...)
```

---

## Observed Runtime Outcome (from logs/tests)

- GP-P02 OpenAI calls repeatedly timeout at ~30s per attempt.
- Each item retries once and can timeout again.
- With multiple per-section calls, total proposal request duration extends beyond client smoke timeout and/or ends with:
  - `PROPOSAL_GENERATION_FAILED` (`All proposal sections failed to generate`).
