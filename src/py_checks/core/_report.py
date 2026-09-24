"""Printing the violations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from py_checks.core._constants import EXIT_OK, EXIT_VIOLATION

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from py_checks.core._violation import Violation


def report(
    *,
    violations: Sequence[Violation],
    root: Path,
    checked: int,
    console: Console | None = None,
) -> int:
    """Prints the violations and returns the exit code.

    Violations go to stderr as plain lines: the editor and CI read them, and
    highlighting must not get in the way of parsing a line. `rich` turns
    colours off by itself when the output is not a terminal — and under
    pre-commit it never is.
    """
    console = console or Console(
        stderr=True,
        soft_wrap=True,
    )
    for violation in violations:
        console.print(
            violation.render(root=root),
            markup=False,
            highlight=False,
        )
    if violations:
        console.print(f"\n{len(violations)} violation(s) in {checked} file(s)", markup=False)
        return EXIT_VIOLATION
    console.print(f"ok: {checked} file(s) checked", markup=False)
    return EXIT_OK
