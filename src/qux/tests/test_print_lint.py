"""Regression guard: no `print(...)` calls in qux source outside the allowlist.

LOG01 convention: qux internal code uses ``logging.getLogger("qux")``.
``print(...)`` is reserved for code whose product IS user-visible CLI output —
the ``qux-install-assets`` console script and Django management commands that
follow Django's CLI convention via ``self.stdout.write``.

This is a lightweight in-tree replacement for ``flake8-print`` / ``ruff``'s T201
rule — keeps the tooling footprint to one linter (pylint) instead of three.
"""

from __future__ import annotations

import ast
from collections.abc import Iterable
from pathlib import Path

from django.test import SimpleTestCase

# Allowlist: relative paths (POSIX style, from src/qux/) where `print(...)` is
# the correct call (CLI output that IS the product). New entries require a
# justification comment.
_ALLOWED = frozenset(
    {
        # qux-install-assets console script main() — user-facing CLI tool.
        "_assets/install.py",
    }
)

_QUX_ROOT = Path(__file__).resolve().parent.parent  # src/qux/


def _python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        # Skip vendored static, generated, and test fixtures.
        parts = set(path.relative_to(root).parts)
        if parts & {"static", "__pycache__", "_assets"} and path.name != "install.py":
            # Allow walking into _assets but skip its non-install.py prints if any.
            continue
        yield path


def _print_call_lines(path: Path) -> list[int]:
    """Return line numbers of bare `print(...)` calls in ``path``.

    Ignores ``print`` references in docstrings / comments — only AST-detected
    calls count. Ignores ``self.stdout.write``, ``sys.stdout.write``, ``logger.info``.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []
    hits: list[int] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                hits.append(node.lineno)
    return hits


class TestNoPrintCalls(SimpleTestCase):
    """Fail if any qux source file outside the allowlist calls `print()`."""

    def test_no_print_calls_outside_allowlist(self):
        offenders: dict[str, list[int]] = {}
        for path in _python_files(_QUX_ROOT):
            rel = path.relative_to(_QUX_ROOT).as_posix()
            if rel in _ALLOWED:
                continue
            # Skip the test files themselves — tests legitimately use print
            # for ad-hoc debugging during development; a forgotten print in a
            # test fails the test author, not production behavior.
            if rel.startswith("tests/") or "/tests/" in rel:
                continue
            lines = _print_call_lines(path)
            if lines:
                offenders[rel] = lines
        self.assertEqual(
            offenders,
            {},
            "print() calls found outside the allowlist. Use logging.getLogger('qux') "
            "or self.stdout.write (in management commands) instead. "
            f"Offenders: {offenders}",
        )
