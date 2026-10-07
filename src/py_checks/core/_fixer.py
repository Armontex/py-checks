"""Applying edits to files."""

from __future__ import annotations

import ast
from collections import defaultdict
from typing import TYPE_CHECKING

from py_checks.core._edit import apply

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from py_checks.core._violation import Violation


def fix(*, violations: Sequence[Violation]) -> tuple[list[Path], list[Violation]]:
    """Fix what can be fixed; return the changed files and what is left.

    A violation without an edit is not a failure of the autofix but an honest
    answer: `*args` cannot be fixed, the argument names are the author's to
    choose. Such violations are returned and go into the report as usual.

    A file the edits leave unparsable is not written: a fix that breaks the
    syntax breaks the next hook too, and that hook names the file, not the
    rule. Its violations go into the report as if there were no edits.
    """
    grouped: dict[Path, list[Violation]] = defaultdict(list)
    for violation in violations:
        grouped[violation.path].append(violation)
    changed: list[Path] = []
    left: list[Violation] = []
    for path, found in grouped.items():
        left.extend(violation for violation in found if violation.edit is None)
        fixable = [violation for violation in found if violation.edit is not None]
        rewritten = _rewrite(
            path=path,
            found=fixable,
        )
        if rewritten is None:
            left.extend(fixable)
        elif rewritten:
            changed.append(path)
    return changed, left


def _rewrite(
    *,
    path: Path,
    found: Sequence[Violation],
) -> bool | None:
    """Whether the file changed; `None` if the edits would break its syntax."""
    edits = [violation.edit for violation in found if violation.edit is not None]
    if not edits:
        return False
    text = path.read_text(encoding="utf-8")
    fixed = apply(
        text=text,
        edits=edits,
    )
    if fixed == text:
        return False
    try:
        ast.parse(fixed, filename=str(path))
    except SyntaxError:
        return None
    path.write_text(fixed, encoding="utf-8")
    return True
