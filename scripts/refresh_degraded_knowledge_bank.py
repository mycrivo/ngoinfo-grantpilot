#!/usr/bin/env python3
"""Post-process an existing degraded knowledge bank: dedupe facts and surface conflicts.

Usage:
  DATABASE_PUBLIC_URL=... python scripts/refresh_degraded_knowledge_bank.py <donor_report_id>

Root cause for STOP_PARSE_FAILED degrades: reconciler JSON exceeded max output tokens (16384).
This script applies the same deterministic optimize step used on new degraded reconciles.
"""

from __future__ import annotations

import json
import os
import sys
import uuid

import psycopg2
from psycopg2.extras import Json


def _label_key(fact: dict) -> str:
    return str(fact.get("semantic_label") or "").strip().lower()


def _value_key(fact: dict) -> str:
    unit = fact.get("unit") or ""
    return f"{json.dumps(fact.get('value'), sort_keys=True, default=str)}::{unit}"


def optimize_facts(raw_facts: dict) -> tuple[dict, list]:
    by_label: dict[str, list[tuple[str, dict]]] = {}
    for fact_key, fact in raw_facts.items():
        if not isinstance(fact, dict):
            continue
        label = _label_key(fact)
        by_label.setdefault(label, []).append((fact_key, fact))

    optimized: dict = {}
    conflicts: list = []

    for _label, entries in by_label.items():
        by_value: dict[str, list[tuple[str, dict]]] = {}
        for fact_key, fact in entries:
            by_value.setdefault(_value_key(fact), []).append((fact_key, fact))

        if len(by_value) > 1:
            primary_key, primary_fact = entries[0]
            conflict_values = []
            for _fact_key, fact in entries:
                prov = fact.get("provenance") or {"excerpt": str(fact.get("value") or "")}
                conflict_values.append(
                    {
                        "value": fact.get("value"),
                        "unit": fact.get("unit"),
                        "source_document_id": fact.get("source_document_id") or "unknown",
                        "source_label": fact.get("source_label") or "Unknown source",
                        "provenance": prov,
                    }
                )
            conflicts.append(
                {
                    "fact_key": primary_key,
                    "conflict_type": "VALUE_MISMATCH",
                    "values": conflict_values,
                    "annotation": (
                        "Same semantic label with differing values from multiple sources; "
                        "human must choose at Gate 1."
                    ),
                    "resolved_value": None,
                    "resolved_at": None,
                }
            )
            optimized[primary_key] = primary_fact
            continue

        bucket = next(iter(by_value.values()))
        primary_key, primary_fact = bucket[0]
        alternate_sources = [fact.get("source_label") for _, fact in bucket[1:] if fact.get("source_label")]
        if alternate_sources:
            note = primary_fact.get("interpretation_note") or ""
            merge = f"Also corroborated in: {', '.join(alternate_sources)}."
            primary_fact = dict(primary_fact)
            primary_fact["interpretation_note"] = f"{note} {merge}".strip()
        optimized[primary_key] = primary_fact

    return optimized, conflicts


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/refresh_degraded_knowledge_bank.py <donor_report_id>")
        return 1

    url = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: DATABASE_PUBLIC_URL or DATABASE_URL required", file=sys.stderr)
        return 1

    report_id = sys.argv[1]
    uuid.UUID(report_id)

    conn = psycopg2.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT knowledge_bank_json FROM donor_reports WHERE id = %s",
                (report_id,),
            )
            row = cur.fetchone()
            if not row:
                print(f"Report not found: {report_id}")
                return 1

            kb = dict(row[0] or {})
            if kb.get("reconciliation_outcome") != "degraded":
                print("Report knowledge bank is not degraded; no-op.")
                return 0

            raw_facts = kb.get("facts") or {}
            before = len(raw_facts)
            optimized, conflicts = optimize_facts(raw_facts)
            kb["facts"] = optimized
            kb["conflicts"] = conflicts

            cur.execute(
                "UPDATE donor_reports SET knowledge_bank_json = %s WHERE id = %s",
                (Json(kb), report_id),
            )
        conn.commit()
        print(f"Optimized degraded KB: facts {before} -> {len(optimized)}, conflicts {len(conflicts)}")
        return 0
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
