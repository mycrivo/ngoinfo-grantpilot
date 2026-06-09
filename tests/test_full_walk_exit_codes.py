"""Audit walk harness — verdict must map to process exit code (P1-3 validation)."""

from scripts.audit.full_walk import PASSING_VERDICTS, exit_code_for_verdict


def test_passing_verdicts_exit_zero():
    for verdict in PASSING_VERDICTS:
        assert exit_code_for_verdict(verdict) == 0


def test_failed_before_gate1_exits_nonzero():
    assert exit_code_for_verdict("failed_before_gate1") == 1


def test_export_incomplete_exits_nonzero():
    assert exit_code_for_verdict("export_incomplete") == 1
