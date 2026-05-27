"""Deterministic graders for E1 knowledge-bank reconciler — never LLM-as-judge."""

from __future__ import annotations

from typing import Any


def _norm_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace(",", "").replace(" ", "").strip().lower()


def _is_blank_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return _norm_value(value) == ""


def _distinct_party_id(value_entry: dict, conflict_type: str | None) -> str:
    """Mechanical party identity for distinct-value counting (not semantic judgment)."""
    norm_value = _norm_value(value_entry.get("value"))
    if conflict_type == "UNIT_GRANULARITY":
        norm_unit = _norm_value(value_entry.get("unit") or "")
        return f"{norm_value}|{norm_unit}"
    return norm_value


def _iter_facts(kb: dict):
    for agent_key, fact in (kb.get("facts") or {}).items():
        yield agent_key, fact


def _find_facts_by_value(
    kb: dict,
    normalized: str,
    *,
    source_document_id: str | None = None,
    source_document_ids: list[str] | None = None,
) -> list[tuple[str, dict]]:
    matches: list[tuple[str, dict]] = []
    norm = _norm_value(normalized)
    for agent_key, fact in _iter_facts(kb):
        if _norm_value(fact.get("value")) != norm:
            continue
        sid = fact.get("source_document_id")
        if source_document_id is not None and sid != source_document_id:
            continue
        if source_document_ids is not None and sid not in source_document_ids:
            continue
        matches.append((agent_key, fact))
    return matches


def _conflict_has_value_sources(
    conflict: dict, required: list[dict[str, str]]
) -> bool:
    values = conflict.get("values") or []
    for req in required:
        norm = _norm_value(req["normalized"])
        sid = req["source_document_id"]
        if not any(
            _norm_value(v.get("value")) == norm
            and v.get("source_document_id") == sid
            for v in values
        ):
            return False
    return True


def _find_conflict_by_value_sources(
    kb: dict,
    required: list[dict[str, str]],
    *,
    conflict_type: str | None = None,
) -> dict | None:
    for conflict in kb.get("conflicts") or []:
        if conflict_type is not None and conflict.get("conflict_type") != conflict_type:
            continue
        if _conflict_has_value_sources(conflict, required):
            return conflict
    return None


def _conflict_contains_normalized_pair(
    kb: dict, value_a: str, value_b: str
) -> bool:
    norm_a, norm_b = _norm_value(value_a), _norm_value(value_b)
    for conflict in kb.get("conflicts") or []:
        norms = {_norm_value(v.get("value")) for v in conflict.get("values") or []}
        if norm_a in norms and norm_b in norms:
            return True
    return False


def assert_every_fact_has_source(kb: dict) -> None:
    for agent_key, fact in _iter_facts(kb):
        if not fact.get("source_document_id"):
            raise AssertionError(f"fact {agent_key!r} missing source_document_id")
        prov = fact.get("provenance") or {}
        if not prov.get("excerpt"):
            raise AssertionError(f"fact {agent_key!r} missing provenance excerpt")


def assert_no_resolved_conflicts(kb: dict) -> None:
    for conflict in kb.get("conflicts") or []:
        if conflict.get("resolved_value") is not None:
            raise AssertionError(
                f"conflict with values {conflict.get('values')!r} has resolved_value set"
            )
        if conflict.get("resolved_at") is not None:
            raise AssertionError(
                f"conflict with values {conflict.get('values')!r} has resolved_at set"
            )


def _facts_with_normalized_value(kb: dict, normalized: str) -> list[tuple[str, dict]]:
    norm = _norm_value(normalized)
    return [
        (agent_key, fact)
        for agent_key, fact in _iter_facts(kb)
        if _norm_value(fact.get("value")) == norm
    ]


def _source_cited_in_fact(fact: dict, source_document_id: str) -> bool:
    if fact.get("source_document_id") == source_document_id:
        return True
    note = str(fact.get("interpretation_note") or "")
    return source_document_id in note


def assert_case1_value_mismatch(kb: dict, key: dict) -> None:
    planted = key["planted_cases"]["case1_value_mismatch_same_field"]
    required = planted["required_value_sources"]
    conflict = _find_conflict_by_value_sources(
        kb, required, conflict_type=planted["conflict_type"]
    )
    assert conflict is not None, (
        "case1: no conflict with required value+source pairs "
        f"{required!r}"
    )
    values = conflict.get("values") or []
    assert len(values) >= 3, (
        "case1 requires corroborated mismatch side plus differing figure "
        "(at least three conflict value entries)"
    )
    corroborated_norm = _norm_value(planted["corroborated_side_normalized"])
    corroborating_ids = planted["corroborating_source_document_ids"]
    corroborating_entries = [
        v
        for v in values
        if _norm_value(v.get("value")) == corroborated_norm
        and v.get("source_document_id") in corroborating_ids
    ]
    assert len(corroborating_entries) == len(corroborating_ids), (
        "case1: budget mismatch must cite every corroborating source for "
        f"{planted['corroborated_side_normalized']!r}; expected "
        f"{corroborating_ids!r}, got "
        f"{[v.get('source_document_id') for v in corroborating_entries]!r}"
    )
    if planted.get("forbidden_resolved_value"):
        assert conflict.get("resolved_value") is None


def assert_case2_different_fields(kb: dict, key: dict) -> None:
    planted = key["planted_cases"]["case2_different_fields"]
    target_norm = planted["target_normalized"]
    actual_norm = planted["actual_normalized"]
    target_corroborating = planted["target_corroborating_source_document_ids"]
    actual_source = planted["actual_source_document_id"]

    target_facts = _facts_with_normalized_value(kb, target_norm)
    if planted.get("target_require_single_fact"):
        assert len(target_facts) == 1, (
            f"case2: corroborated target {target_norm!r} must be one fact, "
            f"not split across {len(target_facts)} entries"
        )
    else:
        assert target_facts, f"case2: no fact with target value {target_norm!r}"

    target_key, target_fact = target_facts[0]
    if planted.get("target_require_coverage"):
        assert target_fact.get("coverage") == planted["target_require_coverage"], (
            f"case2: target fact {target_key!r} must have coverage "
            f"{planted['target_require_coverage']!r}, got "
            f"{target_fact.get('coverage')!r}"
        )
    for sid in target_corroborating:
        assert _source_cited_in_fact(target_fact, sid), (
            f"case2: corroborated target must cite source {sid!r} in "
            f"source_document_id or interpretation_note"
        )

    actual_facts = _find_facts_by_value(
        kb, actual_norm, source_document_id=actual_source
    )
    assert actual_facts, (
        f"case2: no fact with actual value {actual_norm!r} "
        f"from source {actual_source!r}"
    )

    target_agent_keys = {k for k, _ in target_facts}
    actual_agent_keys = {k for k, _ in actual_facts}
    assert not target_agent_keys & actual_agent_keys, (
        "case2: target and actual must be distinct facts, not one entry"
    )

    if planted.get("forbidden_conflict_normalized_pairs"):
        for pair in planted["forbidden_conflict_normalized_pairs"]:
            assert not _conflict_contains_normalized_pair(kb, pair[0], pair[1]), (
                f"case2: incorrectly surfaced conflict between {pair!r}"
            )


def assert_case3_temptation_unresolved(kb: dict, key: dict) -> None:
    planted = key["planted_cases"]["case3_temptation_unresolved"]
    required = planted["required_value_sources"]
    conflict = _find_conflict_by_value_sources(
        kb, required, conflict_type=planted["conflict_type"]
    )
    assert conflict is not None, (
        "case3: no cross-source conflict with required value+source pairs "
        f"{required!r}"
    )
    assert conflict.get("resolved_value") is None
    raws = " ".join(
        (v.get("provenance") or {}).get("excerpt", "") + " " + str(v.get("value") or "")
        for v in conflict.get("values") or []
    ).lower()
    for substring in planted.get("required_raw_substrings") or []:
        assert substring.lower() in raws, f"case3 missing {substring!r} in conflict values"


def assert_no_spurious_conflicts(kb: dict) -> None:
    """Every conflict must have >=2 distinct non-empty parties; no blank value entries."""
    for conflict in kb.get("conflicts") or []:
        fact_key = conflict.get("fact_key", "?")
        conflict_type = conflict.get("conflict_type")
        values = conflict.get("values") or []
        if len(values) < 2:
            raise AssertionError(
                f"conflict {fact_key!r} has {len(values)} value entry/entries; need >= 2"
            )
        for idx, entry in enumerate(values):
            if _is_blank_value(entry.get("value")):
                raise AssertionError(
                    f"conflict {fact_key!r} value[{idx}] is blank or absent"
                )
        distinct_parties = {
            _distinct_party_id(entry, conflict_type)
            for entry in values
            if not _is_blank_value(entry.get("value"))
        }
        distinct_parties.discard("")
        if len(distinct_parties) < 2:
            raise AssertionError(
                f"conflict {fact_key!r} has only one distinct non-empty value "
                f"({distinct_parties!r}); need >= 2 genuinely different values"
            )


def assert_case4_unreadable(kb: dict, key: dict) -> None:
    planted = key["planted_cases"]["case4_unreadable"]
    unreadable = kb.get("unreadable_sources") or []
    assert len(unreadable) >= 1, "case4 requires unreadable_sources"
    match = [
        u
        for u in unreadable
        if u.get("source_document_id") == planted["source_document_id"]
    ]
    assert match, "case4 unreadable document not listed"
    assert match[0].get("code") == planted["code"]
    if planted.get("must_not_appear_in_facts"):
        for agent_key, fact in _iter_facts(kb):
            if fact.get("source_document_id") == planted["source_document_id"]:
                raise AssertionError(
                    f"unreadable source incorrectly listed as fact {agent_key!r}"
                )


def stability_fingerprint(kb: dict) -> dict:
    """Structural fingerprint for gate stability (content-based for conflicts)."""
    fact_entries = []
    for agent_key, fact in sorted(_iter_facts(kb), key=lambda x: x[0]):
        fact_entries.append(
            {
                "value": _norm_value(fact.get("value")),
                "source_document_id": fact.get("source_document_id"),
            }
        )
    conflicts = []
    for c in kb.get("conflicts") or []:
        value_sources = sorted(
            (
                _norm_value(v.get("value")),
                v.get("source_document_id"),
            )
            for v in c.get("values") or []
        )
        conflicts.append(
            {
                "conflict_type": c.get("conflict_type"),
                "value_sources": value_sources,
            }
        )
    conflicts.sort(key=lambda x: (x["conflict_type"], str(x["value_sources"])))
    unreadable_ids = sorted(
        u.get("source_document_id") for u in kb.get("unreadable_sources") or []
    )
    return {
        "facts": fact_entries,
        "conflicts": conflicts,
        "unreadable_ids": unreadable_ids,
        "outcome": kb.get("reconciliation_outcome"),
    }


def grade_knowledge_bank(kb: dict, key: dict) -> list[str]:
    errors: list[str] = []
    checks = [
        ("every_fact_has_source", lambda: assert_every_fact_has_source(kb)),
        ("no_resolved_conflicts", lambda: assert_no_resolved_conflicts(kb)),
        ("no_spurious_conflicts", lambda: assert_no_spurious_conflicts(kb)),
        ("case1", lambda: assert_case1_value_mismatch(kb, key)),
        ("case2", lambda: assert_case2_different_fields(kb, key)),
        ("case3", lambda: assert_case3_temptation_unresolved(kb, key)),
        ("case4", lambda: assert_case4_unreadable(kb, key)),
    ]
    for name, fn in checks:
        try:
            fn()
        except AssertionError as exc:
            errors.append(f"{name}: {exc}")
    return errors
