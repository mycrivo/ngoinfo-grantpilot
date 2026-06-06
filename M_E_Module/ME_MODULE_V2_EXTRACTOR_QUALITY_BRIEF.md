# M&E Module — V2 Extractor Quality Brief

> **Status: PARKED / V2 — do NOT action during current MVP work.**
> This is a research-backed backlog brief, not a build instruction. It captures
> options for raising extraction quality and speed *after* MVP ships and the
> Stage E prod walk has reported a real full-read-vs-degrade rate. Nothing here
> changes the current plan: the D2 resilience parity fix (retry → degrade) is the
> MVP floor and ships as-is. This brief is the deliberate quality pass that comes
> later, prioritised against real data.
>
> **Created:** 2026-05-31 · **Source:** research run against current (May 2026)
> model/parser/runtime landscape, grounded in the D2 prod timeout diagnosis.

---

## 0. Why this exists (the problem, in one paragraph)

The D2 proposal extractor sometimes exceeds its ~90s timeout on a real `.docx`.
The diagnosis established the cause is **output volume, not reading capability**:
the same document extracted cleanly at ~72s producing ~13k tokens of structured
JSON, and the agent is bimodal (same input, sometimes 72s, sometimes >90s). The
MVP fix gives D2 the retry-then-degrade resilience its siblings D3/D4 already have,
so one slow document no longer kills the whole run. **Degrade is a floor, not a
target.** This brief is about raising the *common-case* full-read quality and speed
so degrade stays rare — without conflating "the pipeline survives" with "the
product is good."

**The reframe that drives everything below:** the fix is NOT a better/bigger reader
and NOT new readers. The model tier is correct. The levers are how output is
*produced* and on what *runtime*.

---

## 1. The model tier is right — do NOT upsize it

- Haiku is the current lineup's purpose-built tier for structured entity extraction
  (the high-volume, latency-sensitive case). Moving D2 to Sonnet/Opus would be
  **slower and pricier for no extraction-quality gain** — the task is output-heavy,
  not reasoning-hard.
- Current family (May 2026): Haiku 4.5, Sonnet 4.6, Opus 4.7/4.8 (+ Sonnet 5 on the
  coding lane). Pattern: default Sonnet, escalate Opus on hard problems, downgrade
  Haiku on simple ones. Structured extraction = the downgrade-to-Haiku case.
- **Cheap check worth doing even near-term (config, not a build):** confirm the
  `"haiku"` alias pins to **Haiku 4.5**. Haiku 3 is retired (now errors), so you're
  presumably on 4.5 — but an old/loose alias would be free speed. A config look,
  not scope.

---

## 2. HEADLINE LEVER — adopt native Structured Outputs (now GA)

- **What changed:** Structured Outputs are now **generally available** on the Claude
  API for Haiku 4.5 / Sonnet 4.5 / Opus 4.5 — with expanded schema support,
  **improved grammar-compilation latency**, and a simplified integration path. This
  was not GA when D2 was first built.
- **Why it attacks the root cause:** the latency driver is ~13k tokens of structured
  JSON. Native structured outputs (constrained decoding) forces schema-valid output,
  which cuts parse failures and the retries they trigger, and lowers latency.
  Reliability + speed in one move.
- **ACTION TO VERIFY FIRST (not assume):** determine whether D2 already uses the
  native GA Structured Outputs feature or a tool-use/prompt-coaxed `json_schema`.
  If it is NOT on native Structured Outputs, **this is the highest-value V2 move.**

---

## 3. Runtime — migrate D2–D4 to the Messages API (pairs with #2)

- D2–D4 run on the **Claude Agent SDK**, which spawns the Claude Code CLI as a
  subprocess over stdin/stdout. This is the source of prior auth + stdout-hang bugs,
  and the diagnosis could not rule out subprocess hang as a contributor.
- For a **single** structured extraction call, the subprocess is pure overhead vs a
  direct Messages API HTTP call (the path D1/E1/E3 already use).
- This is the **already-deferred** "migrate D2–D4 → Messages API" decision. Research
  confirms it's the clean V2 spine — and it **pairs with #2**, because Structured
  Outputs is a Messages API capability.
- **Synthesis: #2 and #3 are really ONE combined move** — bring D2–D4 onto the
  direct-API runtime and adopt native structured outputs while there. One migration,
  two wins, removes subprocess uncertainty entirely.

---

## 4. Output volume — trim and/or stream

- Output tokens generate sequentially, so 13k of them *is* the latency.
- **Trim:** reduce the extraction schema to what the reconciler (E1) actually
  consumes downstream — likely not all 13k tokens' worth of fields.
- **Stream:** stream-and-persist incrementally so a slow tail never hits a single
  wall-clock wall.
- Both real, both deferred, both lower priority than #2/#3.

---

## 5. Parser (Docling) — total-latency only, NOT the timeout fix

- **Honest framing:** Docling's ~74s cold parse (downloading 1–2GB of model weights
  on first run) is **outside the D2 90s timer** per the diagnosis. Touching it
  improves total job latency; it does **not** fix the D2 timeout. Don't mis-sell it.
- For `.docx` specifically (programmatic, not scanned), Docling's heavy vision/layout
  models are largely wasted — a lighter path for Office formats would kill the
  cold-start.
- Warm-caching across classify→extract recovers the rest (warm re-parse already
  sub-10s).
- **Lowest priority of everything here.**

---

## 6. D4 — read indicator tables out of `.docx` (capability, deferred)

> **Surfaced by the Stage E prod walk on 0bd9021 (2026-05-31).** Distinct from the
> D4 *resilience* fix, which IS being done in MVP (unsupported/unparseable format →
> degrade, parity with the degraded-timeout path). This item is the *capability*, not
> the resilience — and only the capability is parked.

- **What happened:** an NGO logframe submitted as a `.docx` table was classified
  `indicator_data` and routed to D4's spreadsheet loader, which only accepts
  `.xlsx`/`.csv`. The MVP fix makes that case **degrade** (walk continues to Gate 1,
  indicator data flagged as a gap for the human). It does NOT make the `.docx`
  *readable*.
- **The capability:** actually extract indicator data from a `.docx` table — so a
  charity that submits its logframe as a Word table gets it read, not flagged as a
  gap. This is real extraction work (cells, merged rows, layout), not a format flag.
- **Why deferred:** real NGOs do submit logframes as Word tables, so demand is
  plausible — but it's a genuine extraction feature with its own quality/latency
  surface, not needed to prove or ship Stage E. The MVP degrade path means these
  uploads still reach Gate 1 today; the human confirms the missing indicators. Build
  the reader only when the walk/real usage shows `.docx` indicator tables are common
  enough to be worth it.
- **Scope note when built:** belongs in D4's parse path (add a `.docx`-table reader
  alongside the spreadsheet loader), NOT in D1 re-routing — the classification
  (`indicator_data`) is correct.

---

## 7. E1 reconciler — intermittent invalid-JSON output (resilience done, fix parked)

> **Surfaced by the Stage E prod walks (2026-05-31).** The reconciler (E1) model
> occasionally emits invalid/oversized JSON, causing a degrade. The MVP resilience is
> DONE (pass-through carries candidates forward as unconfirmed + failure observability);
> the underlying *fix* is parked here.

- **What happens:** on some runs E1's model output fails to parse —
  `STOP_PARSE_FAILED` at ~48k chars / ~1,200 lines against `max_tokens=16384`. Two
  failures on one run showed *different* malformations (unterminated string; missing
  delimiter) at *similar large depths* → signature of either token-ceiling truncation
  or loss of JSON discipline over a long structured generation.
- **Bimodal / intermittent:** the same FCDO bundle class passes 4/4 on the gate
  fixture (~49–52 facts) and succeeded on the latest prod walk (33 facts, `complete`).
  It is NOT deterministic — which is exactly why it's parked rather than chased.
- **Already netted (MVP, shipped):** E1 degrade **pass-through** carries the extractor
  candidates into the KB as unconfirmed (`confirmed=False`, `coverage="single_source"`)
  instead of writing an empty KB — so a parse failure is non-fatal to the product.
- **Already instrumented (MVP, shipped):** on parse failure the trace now persists
  `output_tokens` + a bounded raw head/tail snippet, and logs `candidates=N`. **The
  next captured prod failure settles truncation-vs-malformation** — and therefore the
  fix class.
- **The fix (parked, evidence-gated):** if truncation → raise/manage `max_tokens` or
  chunk the bundle; if malformation → **native Structured Outputs** (§2) / the
  **Messages API runtime** path (§3). This is very likely the same lever as §2/§3 —
  i.e. fixing the reconciler's output discipline is the same move as the extractor
  output-reliability work. **Do not pick the fix until the instrumentation captures a
  real failure.**
- **Status:** not yet exercised in prod (reconcile succeeded on the latest walk);
  pass-through + observability proven in suite (151/151).

---

## 8. Indicator `.xlsx` extractor degrading on prod runs (highest-priority watch)

> **Surfaced by the Stage E prod walks (2026-05-31).** The `.xlsx` indicator
> extractor (D4 on a real spreadsheet) **degraded** (likely timeout) on the last two
> walks — the pipeline correctly continued, but the charity's real indicator rows did
> NOT reach the knowledge bank.

- **Why this is the highest-priority parked item:** indicator data is *core* to a
  Monitoring & Evaluation product. A report built without the charity's actual
  outputs/outcomes/beneficiary numbers is missing the substance. Resilience saved the
  run; it did not deliver the value.
- **What we know:** on the d26278c walk the `.xlsx` degraded (timeout, attempt 1/2)
  yet reconcile still produced 33 facts from proposal + award-letter content — so the
  spreadsheet's indicator rows were absent from those 33. Likely the **same latency
  class** as the parked D2 timeout work (Agent SDK subprocess + output volume).
- **Likely shared fix:** the §3 D2–D4 → Messages API migration and/or a realistic
  per-extractor timeout (the D2 `ME_PROPOSAL_TIMEOUT_SECONDS` idea, applied to the
  indicator extractor) probably address this too — it is not a new defect class.
- **Decide against real usage:** watch the `.xlsx` full-read-vs-degrade rate as real
  customers upload spreadsheets. If indicator spreadsheets degrade often, this jumps
  ahead of everything else in the stack — a degraded indicator extractor on a real
  customer's logframe is a direct hit to the product's reason for existing.

---

## 9. V2 priority stack (decide against the real walk data, not now)

Ordered by product impact × evidence-readiness:

1. **Indicator `.xlsx` degrade (§8)** — **highest priority.** Indicator data is core
   to the product; degrading means the charity's real numbers don't reach the report.
   Watch the rate; if spreadsheets degrade often, this leads.
2. **Native Structured Outputs (§2) + D2–D4 → Messages API (§3)** — one combined move.
   Addresses reliability/latency for the extractors AND is the likely fix for the E1
   reconciler JSON failure (§7) and the `.xlsx` timeout (§8). The central lever.
3. **E1 reconciler JSON fix (§7)** — evidence-gated: pick the fix class (token mgmt vs
   structured outputs) only after the instrumentation captures a real prod failure.
   Folds into #2 if it's the malformation case.
4. **Trim / stream the extraction output** — direct attack on the output-volume driver.
5. **`.docx` indicator-table reader for D4 (§6)** — demand-driven capability; build
   when real usage shows `.docx` logframes are common.
6. **Lighten or warm-cache the `.docx` parser path** — total-latency, not the timeout.

**Do NOT:** upsize the model tier; build new readers from scratch. The extractors
exist and read their supported formats correctly — the issues are output reliability,
runtime, and (for D4) one additional input format — not reader capability.

---

## 10. The trigger that decides timing

MVP ships with the parity floor fix → that unblocks the Stage E prod walk → the walk
reports **how often a full clean read happens vs a degrade**:
- **Degrade rare / full reads the norm** → this is a slow-burn quality pass; pull
  items as convenient.
- **Degrade fires often** → lever #1 (Structured Outputs) jumps the queue immediately.

Decide against that real rate, not against the worry. This brief is the V2 input to
that decision.

---

*Parked V2 brief. Not part of current MVP scope. Revisit after the Stage E prod walk
reports a real full-read rate.*
