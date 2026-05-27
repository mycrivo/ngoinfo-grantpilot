# D4 Indicator-Data Gate Audit (Read-Only)

Audit of the last successful live gate invocation for the tabular/indicator extractor (Stage D4). No re-run, no remediation — data as recorded in-repo and from gate stdout at pass time.

**Artifacts:**

- Wall times: `fixtures/indicator_extractor/recorded/gate_wall_times_ms.json`
- Recorded extraction: `fixtures/indicator_extractor/recorded/fcdo_bridgelight_recorded_extraction.json`
- Answer key: `fixtures/indicator_extractor/keys/fcdo_bridgelight_indicator_data_answer_key.json`
- Gate script: `../scripts/indicator_data_gate.py`

---

## 1. `gate_wall_times_ms.json` (full contents)

```json
{
  "correctness_ms": 59407,
  "stability_ms": [
    179853,
    66199,
    44654
  ],
  "spread": {
    "min_ms": 44654,
    "max_ms": 179853,
    "median_ms": 62803,
    "runs": 4
  }
}
```

**Limitation:** This file does **not** store per-run `extraction_outcome`, `num_turns`, `attempt_count`, `degraded_code`, row count, or pass/fail. Only wall-clock milliseconds per slot plus spread summary.

There is no separate gate results array or per-run JSON log in the repository.

---

## 2. Per-run detail (from gate stdout)

The gate script prints one line per run via `_run_once()` but does not persist those fields. The table below is reconstructed from stdout at the **last successful** gate pass.

| Run | Label | extraction_outcome | rows | wall_ms | degraded_code | attempt_count | num_turns |
|-----|--------|-------------------|------|---------|---------------|---------------|-----------|
| 1 | correctness | `complete` | 8 | 59,407 | not logged | not recorded | not recorded |
| 2 | stability_1 | `complete` | 8 | **179,853** | not logged | not recorded | not recorded |
| 3 | stability_2 | `complete` | 8 | 66,199 | not logged | not recorded | not recorded |
| 4 | stability_3 | `complete` | 8 | 44,654 | not logged | not recorded | not recorded |

### ~179,853 ms run (stability_1)

- **Slot:** `stability_ms[0]` → label `stability_1`
- **Outcome:** `complete` (stdout) — not degraded; degraded runs fail the gate and do not write artifacts
- **Retry / attempt_count:** Not persisted on successful runs. `agent_trace.attempt_count` is only set on the degraded terminal path. The recorded fixture (correctness only) shows `attempt_count: null`, `degraded_code: null`
- **stderr during same gate session (once):** `indicator_data_extractor timeout attempt=1/2 ceiling=90.0s` — not bound to a specific run label in saved output; cannot confirm `attempt_count == 2` for stability_1 from disk

Wall time ~180s is consistent with two 90s per-attempt ceilings, but that is inference, not a stored field.

### Correctness `agent_trace` (only run written to recorded fixture)

```json
"agent_trace": {
  "model_used": "haiku",
  "latency_ms": 55311,
  "input_tokens": 16,
  "output_tokens": 10816,
  "max_turns": 3,
  "content_hash": "ad9b0de1724f4039a903fdb21e4788c28fb3db128b820ac33ef50ba2ccb624ee",
  "attempt_count": null,
  "degraded_code": null
}
```

Note: `latency_ms` (55,311) ≠ correctness `wall_ms` (59,407). `max_turns` is the configured cap, not turns consumed. `num_turns` is not a field on `IndicatorDataAgentTrace`.

---

## 3. Gate pass logic

There is no `GATE_PASS` constant. Pass = `_gate()` returns `0` after all checks; artifacts are written only then.

### Correctness

1. Run `extract_indicator_data_from_path` once
2. `grade_extraction_output()` must pass — includes `assert structured.extraction_outcome == "complete"`
3. Build `canonical = stability_fingerprint(correctness)`

### Stability (each of 3 runs)

1. `extraction_outcome` must be `"complete"` — **degraded is excluded** (`if outcome != "complete": return 1`)
2. `stability_fingerprint(result)` must equal `canonical` — content drift fails the gate

### Plain terms

- `extraction_outcome == "degraded"` does **not** count toward a pass for correctness or stability
- Only runs finishing with `complete` (and stability matching fingerprint) allow `PASS` and fixture write

Relevant conditions in `scripts/indicator_data_gate.py`:

```python
grade_extraction_output(correctness.envelope.structured, key)  # requires complete

outcome = result.envelope.structured.extraction_outcome
if outcome != "complete":
    return 1

fp = stability_fingerprint(result.envelope.structured)
if fp != canonical:
    return 1
```

Recorded JSON is **correctness only:** `payload = correctness.envelope.model_dump(mode="json")`.

---

## 4. Recorded fixture — planted checks

Answer key references: `fixtures/indicator_extractor/keys/fcdo_bridgelight_indicator_data_answer_key.json`

### Planted C — row integrity (`hidden_continuation_row`)

Row present in `indicators[]` with ref, name, and locators:

```json
{
  "row_id": "hidden_continuation_row",
  "indicator_ref": {
    "raw": "OP-HIDDEN",
    "cell_state": "stated",
    "source_locator": { "sheet": "Indicators", "cell_range": "B7" }
  },
  "indicator_name": {
    "raw": "District learning meetings held (continuation block)",
    "source_locator": { "sheet": "Indicators", "cell_range": "C7" }
  },
  "source_locator": { "sheet": "Indicators", "cell_range": "A7" }
}
```

(Full entry includes target/actual/unit — see recorded file lines ~372–444.)

### Planted A — no-recompute (`disagg_non_sum`)

Stated total and breakdown both present; not reconciled:

| Field | raw | normalized |
|-------|-----|------------|
| stated_total | 100 | 100 |
| breakdown male | 40 | 40 |
| breakdown female | 35 | 35 |
| breakdown other | 30 | 30 |

Breakdown sum: 40 + 35 + 30 = **105** ≠ stated_total **100**. No `normalized: "105"` on `stated_total` (forbidden adjusted total).

### Cell-state fidelity (`cell_state_demo`)

Three distinct treatments on one row:

| Cell | Field | raw | cell_state / absent |
|------|--------|-----|---------------------|
| Stated zero | target | `"0"` | `stated`, normalized `"0"` |
| Blank | actual | `null` | `absent: true`, `cell_state: null` |
| N/A | unit | `"N/A"` | `not_applicable` |

Not collapsed to a single null/zero representation.

---

## 5. Source row IDs (gate correctness set)

From answer key `source_row_ids` (8 data rows):

1. `op1_1_girls_reenrolled`
2. `op1_2_girls_attending`
3. `disagg_non_sum`
4. `op1_1_target_only`
5. `hidden_continuation_row`
6. `cell_state_demo`
7. `op2_1_latrine_stances`
8. `ocm1_attendance_80pct`

Recorded fixture `structured.summary.total_rows`: 8.

---

## 6. Decision log reference

**D-036** — direct `openpyxl`/csv parse; inherits D-035 timeout pattern (`max_turns=3`, 90s × 2 → `degraded`); gate wall spread min 44,654ms / max 179,853ms / median 62,803ms (4 runs).

See `docs/artefacts/me_module/ME_MODULE_DECISION_LOG.md`.

---

## 7. Re-running the gate (operator note)

```bash
python scripts/indicator_data_gate.py
```

Requires `ANTHROPIC_API_KEY` and `claude` on PATH. Writes recorded fixture and `gate_wall_times_ms.json` only on pass (no retry-until-green).
