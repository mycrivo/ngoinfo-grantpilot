import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / ".cursor" / "hooks"))

from me_module_hooks import check_migration_parity  # noqa: E402


def test_migration_parity_no_warnings():
    warnings = check_migration_parity()
    assert warnings == [], f"Migration parity warnings: {warnings}"
