"""Human-readable scorecard emitter — reports, does not judge.

No threshold, pass mark, baseline, or comparison to expected/prior results.
Does not surface gate_pass as a certification.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.reports.eval.bundle_schema import ScoreableBundle
from app.reports.eval.golden_pack import GoldenPack, load_golden_pack
from app.reports.eval.run_assertions import run_all_layers
from app.reports.eval.verdicts import AssertionResult, Verdict


def _layer_heading(layer: int) -> str:
    names = {
        1: "Layer 1 — fact ledger",
        2: "Layer 2 — conflicts",
        3: "Layer 3 — gaps",
        4: "Layer 4 — report",
        5: "Layer 5 — forbidden outputs",
    }
    return names.get(layer, f"Layer {layer}")


def _partition(results: list[AssertionResult]) -> tuple[list[AssertionResult], list[AssertionResult]]:
    """Split judged results from those with nothing to judge (starvation)."""
    nothing: list[AssertionResult] = []
    judged: list[AssertionResult] = []
    for r in results:
        if r.verdict == Verdict.PASS_BY_STARVATION:
            nothing.append(r)
        else:
            judged.append(r)
    return judged, nothing


def emit_scorecard(
    bundle: ScoreableBundle,
    pack: GoldenPack | None = None,
    *,
    git_commit: str | None = None,
) -> str:
    """Run the assertion library and format a readable scorecard (report only)."""
    pack = pack or load_golden_pack()
    results = run_all_layers(bundle, pack)

    commit = git_commit
    if commit is None:
        commit = str((bundle.meta or {}).get("git_commit") or "")
    run_id = bundle.bundle_id
    exported_at = (bundle.meta or {}).get("exported_at")
    model_config = bundle.model_config or {}

    lines: list[str] = []
    lines.append("# Harness scorecard")
    lines.append("")
    lines.append("This scorecard **reports** assertion outcomes. It does **not** judge,")
    lines.append("certify, set a pass mark, or compare against any expected or prior result.")
    lines.append("")
    lines.append("## Provenance")
    lines.append("")
    lines.append(f"- **git_commit:** `{commit or '(unknown)'}`")
    lines.append(f"- **golden.dataset_version:** `{pack.dataset_version}`")
    lines.append(f"- **golden.content_checksum:** `{pack.content_checksum}`")
    lines.append(f"- **run_id / bundle_id:** `{run_id}`")
    lines.append(f"- **bundle.provenance:** `{bundle.provenance}`")
    if exported_at:
        lines.append(f"- **exported_at:** `{exported_at}`")
    lines.append(f"- **stages_present:** `{list(bundle.stages_present)}`")
    if model_config:
        lines.append("- **model_config (as persisted on bundle):**")
        for k, v in sorted(model_config.items(), key=lambda kv: str(kv[0])):
            lines.append(f"  - `{k}`: `{v}`")
    else:
        lines.append("- **model_config:** `(none transcribed)`")
    lines.append("")

    by_layer: dict[int, list[AssertionResult]] = defaultdict(list)
    for r in results:
        by_layer[r.layer].append(r)

    for layer in sorted(by_layer):
        layer_results = by_layer[layer]
        judged, nothing = _partition(layer_results)
        lines.append(f"## {_layer_heading(layer)}")
        lines.append("")
        lines.append(
            f"_Assertions in this layer: {len(layer_results)} "
            f"(judged: {len(judged)}; nothing to judge / starvation: {len(nothing)})_"
        )
        lines.append("")

        lines.append("### Judged")
        lines.append("")
        if not judged:
            lines.append("_None._")
            lines.append("")
        else:
            for r in judged:
                lines.append(
                    f"- **{r.assertion_id}** — `{r.verdict.value}` "
                    f"[{r.assertion_class.value}] — {r.name}"
                )
                if r.detail:
                    lines.append(f"  - detail: {r.detail}")
                if r.metrics:
                    lines.append(f"  - metrics: `{r.metrics}`")
            lines.append("")

        lines.append("### Nothing to judge (stage absent / starvation)")
        lines.append("")
        if not nothing:
            lines.append("_None._")
            lines.append("")
        else:
            for r in nothing:
                lines.append(
                    f"- **{r.assertion_id}** — `{r.verdict.value}` "
                    f"[{r.assertion_class.value}] — {r.name}"
                )
                if r.detail:
                    lines.append(f"  - detail: {r.detail}")
            lines.append("")

    observations = (bundle.meta or {}).get("observations") or []
    if observations:
        lines.append("## Export observations (from bundle meta)")
        lines.append("")
        for obs in observations:
            lines.append(f"- {obs}")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append(
        "- PASS-BY-STARVATION means the upstream stage was absent from the bundle; "
        "it is not a demonstrated safety property."
    )
    lines.append(
        "- ADVISORY outcomes (including uncalibrated Layer 5 deterministic arm and "
        "uncalibrated prose judge) are reported here and are not certifications."
    )
    lines.append(
        "- No threshold, baseline, ratchet, or expected-result comparison is applied."
    )
    lines.append("")
    return "\n".join(lines)


def scorecard_to_dict(
    bundle: ScoreableBundle,
    pack: GoldenPack | None = None,
    *,
    git_commit: str | None = None,
) -> dict[str, Any]:
    """Structured companion to the markdown scorecard (still non-judging)."""
    pack = pack or load_golden_pack()
    results = run_all_layers(bundle, pack)
    by_layer: dict[str, Any] = {}
    for layer in sorted({r.layer for r in results}):
        layer_results = [r for r in results if r.layer == layer]
        judged, nothing = _partition(layer_results)
        by_layer[str(layer)] = {
            "judged": [r.to_dict() for r in judged],
            "nothing_to_judge": [r.to_dict() for r in nothing],
        }
    return {
        "provenance": {
            "git_commit": git_commit
            if git_commit is not None
            else (bundle.meta or {}).get("git_commit"),
            "golden_dataset_version": pack.dataset_version,
            "golden_content_checksum": pack.content_checksum,
            "run_id": bundle.bundle_id,
            "bundle_provenance": bundle.provenance,
            "exported_at": (bundle.meta or {}).get("exported_at"),
            "stages_present": list(bundle.stages_present),
            "model_config": dict(bundle.model_config or {}),
        },
        "layers": by_layer,
        "report_only": True,
        "no_threshold": True,
        "no_expected_comparison": True,
    }
