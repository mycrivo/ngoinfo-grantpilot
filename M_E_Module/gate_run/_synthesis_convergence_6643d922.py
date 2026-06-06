#!/usr/bin/env python3
"""Synthesis-only convergence run for 6643d922 — prove resumable F1."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
OUT_DIR = REPO / "M_E_Module" / "gate_run"
RID = uuid.UUID("6643d922-150d-4000-b878-4025e7c9145a")
BASE = "https://ngoinfo-grantpilot-production.up.railway.app"
MAX_PASSES = 4
BASELINE_SINGLE_PASS_TOKENS = 109_735  # full-run stage1 artefact (~8 sections, pre-resume era)


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True).strip()


def _is_ancestor(ancestor: str, descendant: str) -> bool:
    a = ancestor if len(ancestor) == 40 else _git("rev-parse", ancestor)
    d = descendant if len(descendant) == 40 else _git("rev-parse", descendant)
    return subprocess.call(["git", "merge-base", "--is-ancestor", a, d], cwd=REPO) == 0


def bootstrap_prod_env() -> dict[str, Any]:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    if not railway:
        raise RuntimeError("railway CLI not found")

    def rv(*extra: str) -> dict:
        return json.loads(
            subprocess.check_output(
                [railway, "variables", "--json", *extra], cwd=REPO, text=True
            )
        )

    pg = rv("--service", "Postgres")
    os.environ["DATABASE_URL"] = pg["DATABASE_PUBLIC_URL"]
    backend = rv("--service", "ngoinfo-grantpilot")
    for key, value in backend.items():
        if value is None or key.startswith("RAILWAY_") or key == "DATABASE_URL":
            continue
        os.environ.setdefault(key, str(value))

    deploys = json.loads(
        subprocess.check_output(
            [railway, "deployment", "list", "--json", "--limit", "1"],
            cwd=REPO,
            text=True,
        )
    )
    deploy_sha = (deploys[0].get("meta") or {}).get("commitHash") if deploys else None
    resume_sha = _git("rev-parse", "a6b430c")
    trim_sha = _git("rev-parse", "628493e")
    concurrency_sha = _git("rev-parse", "d8dd190")

    sys.path.insert(0, str(REPO))
    from app.core.config import get_settings

    get_settings.cache_clear()
    effective_concurrency = get_settings().ME_SYNTHESIS_MAX_CONCURRENCY

    fixes_ok = bool(deploy_sha) and all(
        _is_ancestor(sha, deploy_sha) for sha in (resume_sha, trim_sha, concurrency_sha)
    )

    return {
        "production_target": BASE,
        "railway_project": backend.get("RAILWAY_PROJECT_NAME"),
        "railway_environment": backend.get("RAILWAY_ENVIRONMENT"),
        "deploy_sha": deploy_sha,
        "resume_sha": resume_sha,
        "trim_sha": trim_sha,
        "concurrency_sha": concurrency_sha,
        "fixes_present": fixes_ok,
        "me_synthesis_max_concurrency": int(effective_concurrency),
    }


def section_row(section: dict[str, Any] | None) -> dict[str, Any]:
    if not section:
        return {
            "section_key": None,
            "generation_status": None,
            "failure_reason": None,
            "text_len": 0,
            "human_edited": False,
        }
    content = section.get("content") or {}
    return {
        "section_key": section.get("section_key"),
        "generation_status": section.get("generation_status"),
        "failure_reason": section.get("failure_reason"),
        "text_len": len(content.get("text") or ""),
        "human_edited": bool(section.get("human_edited")),
    }


def snapshot_sections(content_json: dict[str, Any], template_keys: list[str]) -> list[dict[str, Any]]:
    by_key = {
        str(s.get("section_key")): s
        for s in (content_json.get("sections") or [])
        if isinstance(s, dict) and s.get("section_key")
    }
    return [section_row(by_key.get(key)) for key in template_keys]


def incomplete_count(rows: list[dict[str, Any]]) -> int:
    n = 0
    for row in rows:
        status = row.get("generation_status")
        text_len = int(row.get("text_len") or 0)
        if row.get("human_edited"):
            continue
        if status == "ACCEPTED":
            continue
        if status == "GENERATED" and text_len > 0:
            continue
        n += 1
    return n


def is_complete(rows: list[dict[str, Any]]) -> bool:
    return incomplete_count(rows) == 0 and all(
        row.get("generation_status") == "GENERATED" and int(row.get("text_len") or 0) > 0
        for row in rows
        if not row.get("human_edited") and row.get("generation_status") != "ACCEPTED"
    )


def expected_regenerate_keys(
    content_json: dict[str, Any],
    template_keys: list[str],
) -> set[str]:
    from app.reports.schemas.content_json_v1 import section_needs_synthesis, sections_by_key

    existing = sections_by_key(content_json.get("sections") or [])
    return {
        key
        for key in template_keys
        if section_needs_synthesis(existing.get(key))
    }


def preserved_generated_text(
    content_json: dict[str, Any],
    template_keys: list[str],
) -> dict[str, str]:
    from app.reports.schemas.content_json_v1 import section_needs_synthesis, sections_by_key

    existing = sections_by_key(content_json.get("sections") or {})
    out: dict[str, str] = {}
    for key in template_keys:
        sec = existing.get(key)
        if sec is None or section_needs_synthesis(sec):
            continue
        text = str((sec.get("content") or {}).get("text") or "")
        if text:
            out[key] = text
    return out


def make_tracking_query_fn(totals: dict[str, int], called_keys: list[str]):
    from app.core.config import get_settings
    from app.integrations.openai_client import OpenAIClient
    from app.reports.ai.prompts.synthesis import REPORT_SYNTHESIS_SYSTEM_PROMPT
    from app.reports.services.report_synthesis_service import (
        _extract_json_payload,
        _max_tokens_for_section,
        SYNTHESIS_FREQUENCY_PENALTY,
        SYNTHESIS_TEMPERATURE,
    )

    settings = get_settings()
    client = OpenAIClient()
    original_post = client._client.post

    def tracked_post(*args, **kwargs):
        totals["openai_posts"] += 1
        return original_post(*args, **kwargs)

    client._client.post = tracked_post  # type: ignore[method-assign]

    def _query(section_key: str, system_prompt: str, user_prompt: str) -> dict:
        called_keys.append(section_key)
        word_limit = 900
        if '"word_limit":' in user_prompt:
            try:
                idx = user_prompt.index('"word_limit":')
                frag = user_prompt[idx : idx + 40]
                word_limit = int(frag.split(":")[1].split(",")[0].strip())
            except (ValueError, IndexError):
                pass
        response = client.create_chat_completion(
            model=settings.OPENAI_MODEL_PRIMARY,
            fallback_model=settings.OPENAI_MODEL_FALLBACK,
            messages=[
                {"role": "system", "content": system_prompt or REPORT_SYNTHESIS_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=SYNTHESIS_TEMPERATURE,
            top_p=1.0,
            frequency_penalty=SYNTHESIS_FREQUENCY_PENALTY,
            presence_penalty=0.0,
            max_tokens=_max_tokens_for_section(word_limit),
            feature="report_synthesis",
        )
        usage = response.get("usage") or {}
        totals["input_tokens"] += int(usage.get("prompt_tokens") or 0)
        totals["output_tokens"] += int(usage.get("completion_tokens") or 0)
        totals["sections_called"] += 1
        return _extract_json_payload(response)

    return _query


def read_report_state(db) -> tuple[dict[str, Any], list[str]]:
    from app.reports.models.donor_report import DonorReport
    from app.reports.models.funder_report_template import FunderReportTemplate

    report = db.get(DonorReport, RID)
    template = db.get(FunderReportTemplate, report.funder_report_template_id)
    template_keys = [
        str(s["section_key"])
        for s in (template.report_sections_json or [])
        if isinstance(s, dict) and s.get("section_key")
    ]
    return dict(report.content_json or {}), template_keys


def run_one_pass(db) -> dict[str, Any]:
    from app.reports.services.report_synthesis_service import synthesise_and_persist

    content_before, template_keys = read_report_state(db)
    before_rows = snapshot_sections(content_before, template_keys)
    before_incomplete = incomplete_count(before_rows)
    expected_keys = expected_regenerate_keys(content_before, template_keys)
    preserved_before = preserved_generated_text(content_before, template_keys)

    called_keys: list[str] = []
    totals = {
        "input_tokens": 0,
        "output_tokens": 0,
        "sections_called": 0,
        "openai_posts": 0,
    }
    query_fn = make_tracking_query_fn(totals, called_keys)
    t0 = time.monotonic()
    result = asyncio.run(
        synthesise_and_persist(db, RID, query_fn_synthesis=query_fn)
    )
    wall_s = round(time.monotonic() - t0, 1)
    db.expire_all()

    content_after, _ = read_report_state(db)
    after_rows = snapshot_sections(content_after, template_keys)
    after_incomplete = incomplete_count(after_rows)

    retries = max(0, totals["openai_posts"] - totals["sections_called"])

    selection_ok = set(called_keys) == expected_keys
    monotonic_ok = after_incomplete <= before_incomplete and (
        before_incomplete == 0 or after_incomplete < before_incomplete or after_incomplete == 0
    )
    preservation_violations: list[str] = []
    for key, text in preserved_before.items():
        after_sec = next(r for r in after_rows if r["section_key"] == key)
        after_text = ""
        for s in content_after.get("sections") or []:
            if s.get("section_key") == key:
                after_text = str((s.get("content") or {}).get("text") or "")
                break
        if after_text != text:
            preservation_violations.append(key)
        if after_sec.get("generation_status") != "GENERATED":
            preservation_violations.append(f"{key}:status")

    assertions = {
        "monotonic": monotonic_ok,
        "preservation": len(preservation_violations) == 0,
        "selection": selection_ok,
        "preservation_violations": preservation_violations,
    }

    return {
        "before_incomplete": before_incomplete,
        "after_incomplete": after_incomplete,
        "before_rows": before_rows,
        "after_rows": after_rows,
        "expected_regenerate_keys": sorted(expected_keys),
        "called_keys": called_keys,
        "input_tokens": totals["input_tokens"],
        "output_tokens": totals["output_tokens"],
        "openai_posts": totals["openai_posts"],
        "retries_fired": retries,
        "wall_seconds": wall_s,
        "result_generated": result.generated,
        "result_failed": result.failed,
        "assertions": assertions,
        "complete_after_pass": is_complete(after_rows),
    }


def write_markdown(
    path: Path,
    *,
    guards: dict[str, Any],
    baseline: dict[str, Any],
    passes: list[dict[str, Any]],
    verdict: str,
    stop_reason: str | None,
) -> None:
    lines = [
        "# Synthesis convergence run — 2026-06-04",
        "",
        f"**Report:** `{RID}`",
        "",
        "## Precondition guards",
        "",
        f"- Production: {guards['production_target']}",
        f"- Deploy SHA: `{guards['deploy_sha']}`",
        f"- Resume (`a6b430c`) + trim + retry + concurrency fixes present: **{guards['fixes_present']}**",
        f"- `ME_SYNTHESIS_MAX_CONCURRENCY`: {guards['me_synthesis_max_concurrency']}",
        "",
        "## Baseline (pre-loop)",
        "",
        f"- Incomplete sections: **{baseline['incomplete_count']}**",
        f"- GENERATED (non-empty): {baseline['generated_count']}",
        f"- FAILED/empty: {baseline['failed_empty_count']}",
        f"- ACCEPTED: {baseline['accepted_count']}",
        f"- human_edited: {baseline['human_edited_count']}",
        "",
        "| section_key | status | failure | text_len | human_edited |",
        "|-------------|--------|---------|----------|--------------|",
    ]
    for row in baseline["rows"]:
        lines.append(
            f"| {row['section_key']} | {row['generation_status']} | "
            f"{row['failure_reason']} | {row['text_len']} | {row['human_edited']} |"
        )

    cumulative_in = cumulative_out = 0
    lines.extend(["", "## Per-pass results", ""])
    for i, p in enumerate(passes, 1):
        cumulative_in += p["input_tokens"]
        cumulative_out += p["output_tokens"]
        a = p["assertions"]
        lines.extend(
            [
                f"### Pass {i}",
                "",
                f"- Incomplete: {p['before_incomplete']} → {p['after_incomplete']}",
                f"- Regenerated keys: `{p['called_keys']}`",
                f"- Expected keys: `{p['expected_regenerate_keys']}`",
                f"- Tokens in/out: {p['input_tokens']} / {p['output_tokens']}",
                f"- Wall time (s): {p['wall_seconds']}",
                f"- Retries: {p['retries_fired']}",
                f"- Assertions — monotonic: **{a['monotonic']}**, preservation: **{a['preservation']}**, "
                f"selection: **{a['selection']}**",
            ]
        )
        if a.get("preservation_violations"):
            lines.append(f"- Preservation violations: `{a['preservation_violations']}`")
        lines.append("")

    lines.extend(
        [
            "## Cumulative cost vs baseline",
            "",
            f"- Cumulative tokens in/out (all passes): **{cumulative_in} / {cumulative_out}**",
            f"- Reference single full pass (~8 sections, pre-resume): **~{BASELINE_SINGLE_PASS_TOKENS}** input tokens",
            "",
            f"## Verdict: **{verdict}**",
            "",
        ]
    )
    if stop_reason:
        lines.append(f"Stop reason: {stop_reason}")
    lines.append("")
    lines.append("F2 / Gate 3 / export: **not run** (synthesis-only convergence proof).")
    path.write_text("\n".join(lines), encoding="utf-8")


def summarize_baseline(rows: list[dict[str, Any]]) -> dict[str, Any]:
    gen = fail_empty = accepted = human = 0
    for row in rows:
        if row.get("human_edited"):
            human += 1
        if row.get("generation_status") == "ACCEPTED":
            accepted += 1
        elif row.get("generation_status") == "GENERATED" and int(row.get("text_len") or 0) > 0:
            gen += 1
        else:
            fail_empty += 1
    return {
        "rows": rows,
        "incomplete_count": incomplete_count(rows),
        "generated_count": gen,
        "failed_empty_count": fail_empty,
        "accepted_count": accepted,
        "human_edited_count": human,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    guards = bootstrap_prod_env()
    print(json.dumps({"guards": guards}, default=str), flush=True)
    if not guards["fixes_present"]:
        write_markdown(
            OUT_DIR / "SYNTHESIS_CONVERGENCE_2026-06-04.md",
            guards=guards,
            baseline={"rows": [], "incomplete_count": 0, "generated_count": 0,
                      "failed_empty_count": 0, "accepted_count": 0, "human_edited_count": 0},
            passes=[],
            verdict="STOP",
            stop_reason="Deploy missing resume/trim/concurrency fixes",
        )
        return 1

    sys.path.insert(0, str(REPO))
    import app.models  # noqa: F401
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()

    content, template_keys = read_report_state(db)
    baseline_rows = snapshot_sections(content, template_keys)
    baseline = summarize_baseline(baseline_rows)
    print(json.dumps({"baseline": baseline}, default=str), flush=True)

    passes: list[dict[str, Any]] = []
    verdict = "STOP"
    stop_reason: str | None = None

    for pass_num in range(1, MAX_PASSES + 1):
        print(f"=== PASS {pass_num} ===", flush=True)
        pass_data = run_one_pass(db)
        pass_data["pass_number"] = pass_num
        passes.append(pass_data)
        print(json.dumps(pass_data, default=str), flush=True)

        a = pass_data["assertions"]
        if not a["monotonic"]:
            stop_reason = f"Pass {pass_num}: monotonic assertion failed ({pass_data['before_incomplete']} -> {pass_data['after_incomplete']})"
            break
        if not a["preservation"]:
            stop_reason = f"Pass {pass_num}: preservation broken for {a['preservation_violations']}"
            break
        if not a["selection"]:
            stop_reason = (
                f"Pass {pass_num}: selection mismatch expected={pass_data['expected_regenerate_keys']} "
                f"called={pass_data['called_keys']}"
            )
            break
        if pass_data["complete_after_pass"]:
            verdict = "PASS"
            stop_reason = None
            break
    else:
        if passes:
            remaining = passes[-1]["after_rows"]
            incomplete = [
                r for r in remaining
                if r.get("generation_status") != "GENERATED" or int(r.get("text_len") or 0) == 0
            ]
            stop_reason = (
                f"Max {MAX_PASSES} passes reached; incomplete: "
                + ", ".join(
                    f"{r['section_key']}({r.get('failure_reason')})" for r in incomplete if r.get("section_key")
                )
            )

    (OUT_DIR / "synthesis_convergence_passes.json").write_text(
        json.dumps(
            {
                "report_id": str(RID),
                "guards": guards,
                "baseline": baseline,
                "passes": passes,
                "verdict": verdict,
                "stop_reason": stop_reason,
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    write_markdown(
        OUT_DIR / "SYNTHESIS_CONVERGENCE_2026-06-04.md",
        guards=guards,
        baseline=baseline,
        passes=passes,
        verdict=verdict,
        stop_reason=stop_reason,
    )
    db.close()
    print(f"VERDICT={verdict}", flush=True)
    return 0 if verdict == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
