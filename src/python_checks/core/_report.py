"""Вывод нарушений."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rich.console import Console

from python_checks.core._constants import EXIT_OK, EXIT_VIOLATION

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from python_checks.core._violation import Violation


def report(
    *,
    violations: Sequence[Violation],
    root: Path,
    checked: int,
    console: Console | None = None,
) -> int:
    """Печатает нарушения и возвращает код выхода.

    Нарушения идут в stderr обычными строками: их читают редактор и CI, и
    подсветка не должна мешать разбирать строку. Цвета `rich` отключает сам,
    когда вывод идёт не в терминал, — а под pre-commit это всегда так.
    """
    console = console or Console(stderr=True, soft_wrap=True)
    for violation in violations:
        console.print(violation.render(root=root), markup=False, highlight=False)
    if violations:
        console.print(f"\n{len(violations)} нарушени(й) в {checked} файл(ах)", markup=False)
        return EXIT_VIOLATION
    console.print(f"ok: проверено файлов — {checked}", markup=False)
    return EXIT_OK
