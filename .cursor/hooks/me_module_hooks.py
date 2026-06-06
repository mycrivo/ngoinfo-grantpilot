"""Shared hook logic for M&E module governance (Cursor + Claude Code)."""

from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CORE_PREFIXES = (
    "app/api/",
    "app/core/",
    "app/services/",
    "app/models/",
    "app/ai/",
    "app/integrations/",
    "app/schemas/",
    "app/db/",
)

CORE_FILES = {"app/main.py"}

ME_MODELS_DIR = REPO_ROOT / "app" / "reports" / "models"
ME_MIGRATIONS_GLOB = "001[45]_*.py"

REPORTS_IMPORT_RE = re.compile(
    r"(?:^|\n)\s*(?:from\s+app\.reports(?:\.\w+)*\s+import|import\s+app\.reports(?:\.\w+)*)",
    re.MULTILINE,
)

MAIN_PY_ALLOWED_SEAM_RE = re.compile(
    r"if\s+settings\.ME_MODULE_ENABLED\s*:\s*\n\s*from\s+app\.reports\.router\s+import\s+router\s+as\s+reports_router",
    re.MULTILINE,
)

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*=\s*['\"][^'\"]{8,}['\"]"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"whsec_[A-Za-z0-9]+"),
]

EDIT_TOOLS = {"Write", "StrReplace", "ApplyPatch", "EditNotebook", "search_replace"}


def normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def is_core_path(path: str) -> bool:
    normalized = normalize_path(path)
    if normalized.startswith("app/reports/"):
        return False
    if normalized in CORE_FILES:
        return True
    return any(normalized.startswith(prefix) for prefix in CORE_PREFIXES)


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def projected_content(path: Path, tool_name: str, tool_input: dict) -> str | None:
    if tool_name in {"Write", "WriteFile"}:
        return tool_input.get("contents") or tool_input.get("content")
    if tool_name in {"StrReplace", "search_replace"}:
        old = tool_input.get("old_string", "")
        new = tool_input.get("new_string", "")
        current = read_text(path)
        if old and old in current:
            return current.replace(old, new, 1)
        return None
    if tool_name == "ApplyPatch":
        patch = tool_input.get("patch") or tool_input.get("input")
        if isinstance(patch, str) and patch.startswith("*** Update File:"):
            # Best-effort: cannot reliably apply unified patch here; read file as fallback.
            return read_text(path)
    if tool_name == "EditNotebook":
        return tool_input.get("new_string")
    return None


def check_isolation_violation(path: str, content: str) -> str | None:
    if not is_core_path(path):
        return None
    if not REPORTS_IMPORT_RE.search(content):
        return None

    normalized = normalize_path(path)
    if normalized == "app/main.py":
        if MAIN_PY_ALLOWED_SEAM_RE.search(content):
            # Ensure no other app.reports imports outside the allowed block.
            stripped = MAIN_PY_ALLOWED_SEAM_RE.sub("", content)
            if REPORTS_IMPORT_RE.search(stripped):
                return (
                    "app/main.py may only import app.reports.router inside "
                    "`if settings.ME_MODULE_ENABLED:` (single mounting seam)."
                )
            return None
        return (
            "app/main.py must use the single mounting seam: conditional import of "
            "app.reports.router inside `if settings.ME_MODULE_ENABLED:`."
        )

    return (
        f"Isolation violation: core file `{normalized}` must not import app.reports. "
        "M&E imports core; core never imports M&E."
    )


def parse_model_columns(model_path: Path) -> dict[str, set[str]]:
    """Return {table_name: {db_column_names}} from a SQLAlchemy model file."""
    source = read_text(model_path)
    if not source.strip():
        return {}

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}

    tables: dict[str, set[str]] = {}

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        tablename = None
        columns: set[str] = set()
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__tablename__":
                        if isinstance(item.value, ast.Constant) and isinstance(item.value.value, str):
                            tablename = item.value.value
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                col_name = _extract_mapped_column_db_name(item.value)
                if col_name:
                    columns.add(col_name)
                elif item.target.id:
                    columns.add(item.target.id)
        if tablename:
            tables[tablename] = columns
    return tables


def _extract_mapped_column_db_name(node: ast.expr | None) -> str | None:
    if node is None:
        return None
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Name) and func.id == "mapped_column":
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return node.args[0].value
        if isinstance(func, ast.Attribute) and func.attr == "mapped_column":
            if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                return node.args[0].value
    return None


def parse_migration_columns(migration_path: Path) -> dict[str, set[str]]:
    """Return {table_name: {column_names}} from create_table and add_column blocks."""
    source = read_text(migration_path)
    tables: dict[str, set[str]] = {}

    create_table_re = re.compile(
        r'op\.create_table\(\s*["\'](?P<table>[^"\']+)["\']',
        re.MULTILINE,
    )
    column_re = re.compile(
        r'sa\.Column\(\s*["\'](?P<col>[^"\']+)["\']',
        re.MULTILINE,
    )
    add_column_re = re.compile(
        r'op\.add_column\(\s*["\'](?P<table>[^"\']+)["\'],\s*sa\.Column\(\s*["\'](?P<col>[^"\']+)["\']',
        re.MULTILINE,
    )

    matches = list(create_table_re.finditer(source))
    for index, match in enumerate(matches):
        table = match.group("table")
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        chunk = source[start:end]
        cols = {m.group("col") for m in column_re.finditer(chunk)}
        if cols:
            tables.setdefault(table, set()).update(cols)

    for match in add_column_re.finditer(source):
        tables.setdefault(match.group("table"), set()).add(match.group("col"))

    return tables


def check_migration_parity() -> list[str]:
    warnings: list[str] = []
    if not ME_MODELS_DIR.exists():
        return warnings

    model_tables: dict[str, set[str]] = {}
    for model_file in sorted(ME_MODELS_DIR.glob("*.py")):
        if model_file.name == "__init__.py":
            continue
        for table, cols in parse_model_columns(model_file).items():
            model_tables.setdefault(table, set()).update(cols)

    if not model_tables:
        return warnings

    migration_dir = REPO_ROOT / "alembic" / "versions"
    migration_tables: dict[str, set[str]] = {}
    for migration_file in sorted(migration_dir.glob(ME_MIGRATIONS_GLOB)):
        for table, cols in parse_migration_columns(migration_file).items():
            migration_tables.setdefault(table, set()).update(cols)

    for table, model_cols in sorted(model_tables.items()):
        mig_cols = migration_tables.get(table)
        if mig_cols is None:
            warnings.append(
                f"Migration parity: model defines table `{table}` but no matching "
                f"0014_me_module_*.py create_table found."
            )
            continue
        missing_in_migration = model_cols - mig_cols
        missing_in_model = mig_cols - model_cols
        if missing_in_migration:
            warnings.append(
                f"Migration parity: table `{table}` columns in model but not migration: "
                f"{sorted(missing_in_migration)}"
            )
        if missing_in_model:
            warnings.append(
                f"Migration parity: table `{table}` columns in migration but not model: "
                f"{sorted(missing_in_model)}"
            )
    return warnings


def scan_text_for_secrets(text: str, label: str) -> list[str]:
    hits: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(f"Possible secret pattern in {label}: {pattern.pattern}")
    return hits


def scan_staged_files_for_secrets() -> list[str]:
    hits: list[str] = []
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return ["Secret scan: git not available."]

    if result.returncode != 0:
        return [f"Secret scan: git diff --cached failed: {result.stderr.strip()}"]

    for rel_path in result.stdout.splitlines():
        rel_path = rel_path.strip()
        if not rel_path or rel_path.startswith("docs/"):
            continue
        full = REPO_ROOT / rel_path
        if not full.is_file():
            continue
        if full.suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".docx"}:
            continue
        content = read_text(full)
        hits.extend(scan_text_for_secrets(content, rel_path))
    return hits


def read_hook_input() -> dict:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def emit_json(payload: dict) -> None:
    sys.stdout.write(json.dumps(payload))
    sys.stdout.flush()


def emit_deny(user_message: str, agent_message: str) -> None:
    emit_json(
        {
            "permission": "deny",
            "user_message": user_message,
            "agent_message": agent_message,
        }
    )


def emit_allow() -> None:
    emit_json({"permission": "allow"})


def emit_additional_context(message: str) -> None:
    emit_json({"additional_context": message})
