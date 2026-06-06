# GrantPilot M&E — Cost & Per-Report Tracing Brief (PARKED)

> **Status:** PARKED — not an MVP build blocker. Sits alongside
> `ME_MODULE_V2_EXTRACTOR_QUALITY_BRIEF.md` as deferred work.
> **Do NOT pull any of this into the Stage F build track.** Cost/revenue stays
> out of build sequencing by standing principle. Return to this **after the F
> quality gate passes, before launch (Stage K)**.
> **Created:** 2026-06-01 · **Author:** Claude (CTO) at Pranab's direction.

---

## 0. WHY THIS IS PARKED (read first)

Pranab flagged Claude API spend and the need to land the right per-report cost
mix. The investigation (2026-06-01) concluded there is **no margin emergency and
nothing to optimise yet** — because we have never measured a single clean
end-to-end report. Optimising now would mean tuning against a number we don't
have, and it would contaminate the build sequence. So: capture the picture, park
it, build F. The only cost action that belongs in the near term is **measurement**
(see §4), and it rides on the F1 prose walk we were already going to run — it is
not separate work.

---

## 1. SNAPSHOT AS OF 2026-06-01

Source: Anthropic Console (Cost + Caching views) and a token-usage CSV export
(`ngoinfo-m&e-api-key`, Default workspace).

- **Total Claude spend: USD 18.60** — and all of it landed **2026-05-25 →
  2026-05-31** (six days), not across a 30-day window. This is **build/test
  burn**: repeated smoke walks on the same FCDO bundle, extraction retries, gate
  resume testing. It is **not** a per-report unit cost.
- **OpenAI (gpt-5.4 / F1 synthesis) spend: ~zero so far** — F1 was tested against
  a mocked generator; no real synthesis tokens have been spent yet.
- **Web search / code execution / session runtime cost: USD 0.00** — we use none
  of those.

### Token mix by Claude model (the important part)
| Model | Total input tokens | Output tokens | Role (inferred) | Cache-read share of input |
|-------|--------------------|---------------|-----------------|---------------------------|
| **Haiku 4.5** | ~5.32M | ~1.63M | D1–D4 extraction/classification (bulk grunt work) | **~60%** |
| **Opus 4.7** | ~0.28M | ~0.11M | E1 reconciler / E3 gap (heavy reasoning, used sparingly) | **~58%** |
| **Sonnet 4.6** | ~0.33M | ~0.20M | mid-tier reasoning | **0%** |

---

## 2. WHAT THE DATA ALREADY TELLS US (locked conclusions)

1. **The model tiering is correct.** The overwhelming majority of token volume is
   on the cheapest model (Haiku) doing extraction; the expensive model (Opus) is
   used only in small volume for judgment. This is the single most important
   cost-control decision in an agent product and it is **already right by design**
   — no rework needed.
2. **Build burn ≠ unit cost.** $18.60 over six days of heavy iteration is a
   rounding error and tells us nothing reliable about what a customer report
   costs. Do not manage the business against this number.
3. **Prompt caching is already active where it matters.** Despite the console
   banner saying "you're not using prompt caching" (the banner **lags the data**),
   the CSV shows ~58–60% of Haiku and Opus input is served from cache reads — i.e.
   the big input-cost lever the console advertises (50–90%) is **mostly already
   captured** on the high-volume Claude side. The only model with 0% caching is
   Sonnet, a small slice.
4. **Per-report cost is a TWO-VENDOR number.** Claude tokens for the six
   reasoning/extraction agents (D1, D2, D3, D4, E1, E3) **plus the forthcoming F2
   critic**, AND OpenAI `gpt-5.4` for F1's eight synthesis sections. Any true
   per-report figure must sum both.
5. **The capture mechanism already exists.** `agent_trace_json` records per-run
   cost accounting. We have simply never run one isolated report and tallied it.

### Orientation (NOT a measured claim)
The existing proposal product runs ~**$1.25 per complete proposal**. Impact Pro
allocates ~**$49.50 of revenue per report** (2 reports / $99 mo). Even at several
times the proposal cost, an M&E report plausibly lands in **low single-digit
dollars** against a ~$49.50 envelope. Comfortable margin. The cost ceiling
(memory §5: "per-report model cost must stay well inside per-report revenue with
margin") is not at risk on current evidence.

---

## 3. PICKUP CHECKLIST (when we return, post-F-gate, pre-launch)

Do these in order; stop if the baseline (item 1) already clears the ceiling
comfortably — most of the rest may prove unnecessary.

1. **Establish the real baseline.** From the instrumented F1/F2 walk (§4), read
   the first true **two-vendor per-report cost** for one clean report. This is the
   number we manage against the ceiling. Everything below is optional optimisation
   judged against it.
2. **Decide if optimisation is even warranted.** If baseline ≪ ceiling (likely),
   park optimisation entirely until real usage data says otherwise. Effort follows
   proven need.
3. **If warranted — Sonnet caching.** Sonnet is the one model at 0% cache. Confirm
   whether any agent on Sonnet re-sends stable context (system prompt, funder
   template, humaniser rules) and could cache it.
4. **If warranted — OpenAI / F1 caching.** Synthesis re-sends the funder template
   + humaniser rules across eight section calls per report. Assess prompt caching
   / shared-prefix reuse on the OpenAI side.
5. **If warranted — model right-sizing.** Re-check whether any agent currently on
   Opus could drop to Sonnet/Haiku without quality loss, and whether F1's
   synthesis model (open item, memory §17) should move off gpt-5.4 to a cheaper
   class — **benchmark, don't guess.**
6. **Cost observability for ops.** Decide whether to surface per-report cost in an
   internal view (from `agent_trace_json`) so we can watch unit economics as real
   reports flow at launch.

---

## 4. THE ONE NEAR-TERM ACTION (rides on the F1 walk — not separate work)

When the F1 prose walk runs on the parked FCDO checkpoint, **instrument it to
record the full two-vendor cost for that single report via `agent_trace`** —
OpenAI for synthesis, Claude for everything upstream — so the walk produces our
**first true per-report unit cost alongside the prose**. When F2 (critic) lands,
it adds a known, measured Claude increment on top. This is the only cost work that
happens before launch; it is measurement, not optimisation, and it does not change
the F build sequence.

---

## 5. NON-GOALS NOW (STOP-and-flag if build drifts here)

- No caching refactor, no model swaps, no cost-optimisation sprint during Stage F.
- No cost logic added to the build track. Cost stays out of build sequencing.
- No managing decisions off the $18.60 build-burn figure.

---

*End of parked brief. Re-enter only after the F quality gate passes. The build
focus returns to Stage F: F1 prose walk (with two-vendor cost capture) → F2 critic
→ Gate 3 → the joint quality gate.*
