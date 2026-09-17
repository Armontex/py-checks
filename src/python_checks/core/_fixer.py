"""Наложение правок на файлы."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from python_checks.core._edit import apply

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from python_checks.core._violation import Violation


def fix(*, violations: Sequence[Violation]) -> tuple[list[Path], list[Violation]]:
    """Исправить, что умеем; вернуть изменённые файлы и то, что осталось.

    Нарушение без правки — не провал автофикса, а честный ответ: `*args`
    исправить нельзя, имена аргументов придумывает автор. Такие нарушения
    возвращаются и попадают в отчёт как обычно.
    """
    grouped: dict[Path, list[Violation]] = defaultdict(list)
    for violation in violations:
        grouped[violation.path].append(violation)
    changed: list[Path] = []
    left: list[Violation] = []
    for path, found in grouped.items():
        left.extend(violation for violation in found if violation.edit is None)
        if _rewrite(path=path, found=found):
            changed.append(path)
    return changed, left


def _rewrite(*, path: Path, found: Sequence[Violation]) -> bool:
    edits = [violation.edit for violation in found if violation.edit is not None]
    if not edits:
        return False
    text = path.read_text(encoding="utf-8")
    fixed = apply(text=text, edits=edits)
    if fixed == text:
        return False
    path.write_text(fixed, encoding="utf-8")
    return True
