# P3-2 — Worker stall / orphan-reaper sightings (live)

Reliability gap: extract (or other long stage) runs with no worker heartbeat; orphan reaper aborts after idle timeout. **Not a moat/fence regression.**

| # | Date | Report ID | Run | Stage hung | Notes |
|---|------|-----------|-----|------------|-------|
| 1 | 2026-06-09 | `25ebfaad-7f8d-4130-978e-1c31ac52c609` | `p1_clean_docset` (CI [27202457869](https://github.com/mycrivo/ngoinfo-grantpilot/actions/runs/27202457869)) | **extract** (~39m idle) | Verdict `failed_before_gate1`; orphan reaper: `no worker progress since classify completed`. First live P3-2 sighting. Harness masked green (exit 0) until fixed in follow-up commit. |
