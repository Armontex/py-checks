"""Длина функции."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from pydantic import Field

from python_checks.checks.signatures._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "function-length"

Function = ast.FunctionDef | ast.AsyncFunctionDef


class FunctionLengthSettings(CheckSettings):
    max_lines: int = Field(default=50, gt=0)


class FunctionLength:
    """Падает, если функция длиннее лимита.

    Функция сверх этой длины прячет в себе вторую. Считается тело как
    написано — пустые строки и комментарии тоже: читателю держать в голове
    приходится их все. Декораторы и сигнатура, разложенная по строкам, не
    считаются: они описывают функцию, а не работу, которую она делает.

    Считать инструкции вместо строк (ruff `PLR0915`) — не то же самое, и на
    этих сервисах разница решающая: самая длинная функция в четырёх
    репозиториях — 91 строка и две инструкции, а с предела в 50 инструкций не
    падает ни одна функция из трёх с лишним тысяч файлов.

    Вложенная функция считается отдельно и в длину внешней входит: это строки,
    которые читатель всё равно проходит.

    Пометка снимается с любой строки сигнатуры.

    Настройка: `max-lines`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = FunctionLengthSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(cls, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        limits = settings_as(settings=settings, model=FunctionLengthSettings, code=CODE)
        for node in ast.walk(file.tree):
            if not isinstance(node, Function):
                continue
            length = cls._length(node=node)
            if length <= limits.max_lines:
                continue
            yield Violation(
                path=file.path,
                line=node.lineno,
                column=node.col_offset + 1,
                code=CODE,
                message=f"{node.name}: {length} строк, предел {limits.max_lines}",
                # Пометка снимается с любой строки сигнатуры: у функции с
                # аргументами в столбик она стоит на той, что сигнатуру
                # закрывает, а не на `def`.
                end_line=max(node.lineno, node.body[0].lineno - 1),
            )

    @staticmethod
    def _length(*, node: Function) -> int:
        """Строки тела: от первой инструкции до конца последней."""
        first = node.body[0]
        last = node.body[-1]
        return (last.end_lineno or last.lineno) - first.lineno + 1
