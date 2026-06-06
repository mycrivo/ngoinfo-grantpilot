#!/usr/bin/env python3
"""Throwaway read-only unicode audit for KB key diagnosis."""
from __future__ import annotations

import json
import shutil
import subprocess
import unicodedata
from pathlib import Path

from sqlalchemy import create_engine, text

REPO = Path(__file__).resolve().parents[1]


def char_audit(s: str) -> list[tuple]:
    out = []
    for i, ch in enumerate(s):
        o = ord(ch)
        if ch.isdigit() or o > 127 or (o < 32 and ch not in "\t\n\r"):
            out.append((i, ch, f"U+{o:04X}", unicodedata.name(ch, "?")))
    return out


def is_bengali_digit(ch: str) -> bool:
    return "\u09E6" <= ch <= "\u09EF"


def digit_classes(s: str) -> dict[str, list[str]]:
    classes: dict[str, list[str]] = {"ascii": [], "bengali": [], "other": []}
    for ch in s:
        if "0" <= ch <= "9":
            classes["ascii"].append(ch)
        elif is_bengali_digit(ch):
            classes["bengali"].append(ch)
        elif ch.isdigit():
            classes["other"].append(ch)
    return classes


def walk_strings(obj, path: str = "", hits: list | None = None) -> list[tuple[str, str, list]]:
    if hits is None:
        hits = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            kp = f"{path}.{k}" if path else str(k)
            if isinstance(k, str):
                a = char_audit(k)
                if a:
                    hits.append((kp + " [KEY]", k, a))
            walk_strings(v, kp, hits)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_strings(v, f"{path}[{i}]", hits)
    elif isinstance(obj, str):
        a = char_audit(obj)
        if a:
            hits.append((path, obj, a))
    return hits


def main() -> None:
    railway = shutil.which("railway.cmd") or shutil.which("railway")
    pg = json.loads(
        subprocess.check_output(
            [railway, "variables", "--json", "--service", "Postgres"],
            cwd=REPO,
            text=True,
        )
    )
    engine = create_engine(pg["DATABASE_PUBLIC_URL"])

    reports = [
        "5026ab66-9e30-413b-a823-7931c16fe435",
        "cabb8796-195b-4089-afab-94d6fe841d50",
    ]

    for rid in reports:
        print("\n" + "=" * 70)
        print("REPORT", rid)
        with engine.connect() as conn:
            kb = conn.execute(
                text(
                    "SELECT knowledge_bank_json, content_json FROM donor_reports "
                    "WHERE id = CAST(:rid AS uuid)"
                ),
                {"rid": rid},
            ).mappings().first()
            docs = list(
                conn.execute(
                    text(
                        "SELECT id, original_filename, extracted_json FROM uploaded_documents "
                        "WHERE donor_report_id = CAST(:rid AS uuid)"
                    ),
                    {"rid": rid},
                ).mappings().all()
            )

        facts = (kb["knowledge_bank_json"] or {}).get("facts") or {}
        print(f"KB facts: {len(facts)}")
        sample_key = None
        for k in sorted(facts):
            dc = digit_classes(k)
            if dc["bengali"] or dc["other"]:
                if sample_key is None:
                    sample_key = k
                print(" CORRUPT KEY", repr(k), "digits", dc)
                print("  audit", char_audit(k)[:8])
        if not sample_key:
            for k in sorted(facts):
                if "op2_1" in k or "op3_1" in k:
                    print(" CLEAN KEY sample", repr(k), digit_classes(k))
                    sample_key = k
                    break

        corrupt_vals = 0
        for k, v in facts.items():
            if isinstance(v, dict) and v.get("value") is not None:
                s = str(v["value"])
                if char_audit(s):
                    corrupt_vals += 1
                    print(" CORRUPT VALUE", k, repr(s), char_audit(s)[:4])
        print(f"Corrupt values in facts: {corrupt_vals}")

        for doc in docs:
            fn = doc["original_filename"]
            if "xlsx" not in fn.lower():
                continue
            ej = doc["extracted_json"] or {}
            struct = ej.get("structured") or ej
            print(f"\nXLSX extract: {fn}")
            hits = walk_strings(struct)
            bengali_hits = [
                h for h in hits if any(is_bengali_digit(c) for _, c, _, _ in h[2])
            ]
            print(f"  string hits with non-ascii/control: {len(hits)}")
            print(f"  hits with Bengali digits: {len(bengali_hits)}")
            for path, s, a in bengali_hits[:15]:
                print(f"   {path}: {repr(s[:80])} -> {a[:5]}")
            # indicator rows
            for i, row in enumerate((struct.get("indicators") or [])[:12]):
                ref = row.get("indicator_ref") or {}
                norm = ref.get("normalized") if isinstance(ref, dict) else None
                if norm:
                    dc = digit_classes(str(norm))
                    if dc["bengali"]:
                        print(f"  row[{i}] indicator_ref.normalized BENGALI", repr(norm))

        # evidence_used vs KB keys for critic mismatch
        content = kb.get("content_json") or {}
        eu_keys = set()
        for sec in content.get("sections") or []:
            for ref in (sec.get("content") or {}).get("evidence_used") or []:
                if ref.startswith("fact:"):
                    eu_keys.add(ref[5:])
        kb_keys = set(facts)
        missing = sorted(eu_keys - kb_keys)
        print(f"\nevidence_used fact keys not in KB: {len(missing)}")
        for m in missing[:12]:
            print(" ", repr(m), digit_classes(m))
            # fuzzy match
            ascii_m = m.encode("ascii", "ignore").decode()
            for kk in kb_keys:
                if kk.replace("_", "") == m.replace("_", "") or ascii_m in kk:
                    print("   near KB key", repr(kk), digit_classes(kk))

        # prose control chars
        for sec in content.get("sections") or []:
            text_body = (sec.get("content") or {}).get("text") or ""
            ctrl = char_audit(text_body)
            ctrl = [c for c in ctrl if c[2] in ("U+0010", "U+000B", "U+000C") or c[2].startswith("U+00") and int(c[2][2:], 16) < 32]
            if ctrl:
                print(f" PROSE CTRL {sec.get('section_key')}", ctrl[:5])


if __name__ == "__main__":
    main()
