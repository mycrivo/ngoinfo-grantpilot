#!/usr/bin/env python3
"""Run governance guards over staged or range diffs (pre-commit + CI)."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".cursor" / "hooks"
sys.path.insert(0, str(HOOKS_DIR))

from governance_guards import (  # noqa: E402
    evaluate_added_map,
    format_violations,
    load_blocklist,
    parse_unified_diff_added,
    staged_added_lines,
)


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def resolve_ci_range(rev_range: str) -> str:
    """Normalize A...B or A..B to merge-base..head (two-dot)."""
    raw = rev_range.strip()
    if "..." in raw:
        left, right = raw.split("...", 1)
    elif ".." in raw:
        left, right = raw.split("..", 1)
    else:
        return raw
    left = left.strip()
    right = right.strip()
    if not left or not right:
        return raw
    mb = _git_output(["merge-base", left, right]).strip()
    if not mb:
        raise RuntimeError(f"git merge-base failed for {left} {right}")
    return f"{mb}..{right}"


def commits_in_range(rev_range: str) -> list[str]:
    # Always evaluate merge-base..head so symmetric three-dot ranges cannot
    # smuggle shared history past the per-commit protected-file check.
    resolved = resolve_ci_range(rev_range)
    out = _git_output(["rev-list", "--reverse", resolved])
    return [line.strip() for line in out.splitlines() if line.strip()]


def commit_message(sha: str) -> str:
    return _git_output(["log", "-1", "--format=%B", sha])


def commit_added_map(sha: str) -> dict[str, list[str]]:
    diff = _git_output(["show", "--format=", "-U0", "--no-color", sha])
    return parse_unified_diff_added(diff)


PROTECTED_FILE_POST_MERGE_NOTE = (
    "Protected-file authorisation is established by review at PR time "
    "(D-078); on non-PR CI events the protected-file check reports only. "
    "Funder/fixture, harness-import, and secret guards remain blocking "
    "on every event — no override, no soft mode."
)


def partition_ci_violations(
    violations: list,
    *,
    protected_file_mode: str,
) -> tuple[list, list]:
    """Split violations into (blocking, report_only) for CI event asymmetry.

    protected_file_mode:
      - "blocking": all guards fail the job (pull_request)
      - "report": protected_file is report-only; other guards still block (push/schedule)
    """
    mode = (protected_file_mode or "blocking").strip().lower()
    if mode not in {"blocking", "report"}:
        raise ValueError(
            f"protected_file_mode must be 'blocking' or 'report', got {protected_file_mode!r}"
        )
    if mode == "blocking":
        return list(violations), []
    blocking = [v for v in violations if v.guard != "protected_file"]
    report_only = [v for v in violations if v.guard == "protected_file"]
    return blocking, report_only


def _print_overrides(overrides: list[dict], *, sha: str | None = None) -> None:
    for ov in overrides:
        path = ov.get("path", "")
        reason = ov.get("reason", "")
        if sha is not None:
            print(
                f"governance: override sha={sha} path={path} reason={reason!r}",
                file=sys.stderr,
            )
        else:
            print(
                f"governance: override path={path} reason={reason!r}",
                file=sys.stderr,
            )


def main() -> int:
    parser = argparse.ArgumentParser(description="GrantPilot governance guards")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--staged", action="store_true", help="Scan staged diff")
    group.add_argument("--range", dest="rev_range", help="Scan git rev range (A...B)")
    parser.add_argument("--layer", default="ci", help="Layer label for override log")
    parser.add_argument(
        "--commit-message-file",
        help="Optional path to commit message for override detection",
    )
    parser.add_argument(
        "--allow-env-override",
        action="store_true",
        help="Allow GOVERNANCE_OVERRIDE from the environment (local pre-commit only)",
    )
    parser.add_argument(
        "--protected-file-mode",
        choices=("blocking", "report"),
        default="blocking",
        help=(
            "CI only: 'blocking' fails on protected-file (pull_request); "
            "'report' prints protected-file findings without failing "
            "(push/schedule). Other guards always block."
        ),
    )
    args = parser.parse_args()

    # CI must never honour a workflow-injected GOVERNANCE_OVERRIDE env var.
    if not args.allow_env_override and not args.staged:
        os.environ.pop("GOVERNANCE_OVERRIDE", None)

    if args.staged:
        added = staged_added_lines()
        if args.commit_message_file:
            commit_message_text = Path(args.commit_message_file).read_text(encoding="utf-8")
        else:
            commit_message_text = ""
        if not args.allow_env_override:
            # Staged local runs still allow env (pre-commit sets this implicitly by
            # not clearing). Default: keep env for staged.
            pass
        layer = args.layer or "pre-commit"
        result = evaluate_added_map(
            added,
            layer=layer,
            commit_message=commit_message_text,
            check_protected=True,
            log_overrides=True,
        )
        if not result.ok:
            print(format_violations(result.violations, load_blocklist()), file=sys.stderr)
            return 1
        if result.overrides:
            _print_overrides(result.overrides)
        elif result.override_used:
            print(
                f"governance: protected-file override accepted ({result.override_reason!r})",
                file=sys.stderr,
            )
        # log_override() appends after the staged snapshot is fixed; re-stage so
        # the audit trail ships in the same commit (AGENTS.md: logged + visible).
        if result.overrides or result.override_used:
            log_rel = ".governance/override_log.jsonl"
            subprocess.run(
                ["git", "add", "--", log_rel],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            print(f"governance: restaged {log_rel} for commit", file=sys.stderr)
        print("governance: OK")
        return 0

    # Per-commit evaluation: an override in commit A must not authorize
    # protected-file changes introduced in commit B.
    resolved = resolve_ci_range(args.rev_range)
    shas = commits_in_range(resolved)
    if not shas:
        print("governance: OK (empty commit range)")
        return 0

    all_violations = []
    any_override = False
    for sha in shas:
        added = commit_added_map(sha)
        if not added:
            continue
        msg = commit_message(sha)
        # Clear env so only this commit's message can authorize protected writes.
        os.environ.pop("GOVERNANCE_OVERRIDE", None)
        result = evaluate_added_map(
            added,
            layer="ci",
            commit_message=msg,
            check_protected=True,
            log_overrides=True,
        )
        if result.overrides:
            any_override = True
            _print_overrides(result.overrides, sha=sha)
        elif result.override_used:
            any_override = True
            print(
                f"governance: override sha={sha} path=* reason={result.override_reason!r}",
                file=sys.stderr,
            )
        all_violations.extend(result.violations)

    blocking, report_only = partition_ci_violations(
        all_violations, protected_file_mode=args.protected_file_mode
    )
    if args.protected_file_mode == "report":
        print(f"governance: {PROTECTED_FILE_POST_MERGE_NOTE}", file=sys.stderr)
        if report_only:
            print(
                "governance: protected-file findings (report-only on this event):",
                file=sys.stderr,
            )
            print(format_violations(report_only, load_blocklist()), file=sys.stderr)
    if blocking:
        print(format_violations(blocking, load_blocklist()), file=sys.stderr)
        return 1
    if any_override:
        print("governance: protected-file override(s) accepted (see trail above)", file=sys.stderr)
    print("governance: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
