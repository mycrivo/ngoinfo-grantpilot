# Package specs

One file per package, named by its ID from `docs/ME_V2_MASTER_TASK_LIST.md` (for example `P3.2.md`). The file is the spec; agents read files, not chat.

Every spec has these sections, in this order:

1. **Problem** — what is wrong or missing, in one paragraph, with evidence pointers (audit section, run id, test).
2. **Decisions verbatim** — the decision-log entries and contract sections that govern this package, quoted, not paraphrased.
3. **Fence** — files and modules the implementer may touch. Anything else requires a stop.
4. **Invariants** — what must remain true (isolation, kill switch, resume, quota, guard).
5. **Acceptance** — numbered lines. Each becomes one contract test. Written in observable terms (fixture in, state or output out), never in terms of implementation.
6. **Tier and STOP condition** — GREEN / AMBER / OWNER, and the exact condition under which the agent stops and reports.
7. **Out of scope** — what a well-meaning agent might do here and must not.
8. **Owner-triggered verification** — the live run the owner performs after the audit, if any.

Specs contain no file paths as commands, no function names, no code. They say what and why; the implementer decides how, within the contracts.
