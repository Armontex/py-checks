"""Длина функции."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from pydantic import Field

from py_checks.checks.signatures._functions import definitions
from py_checks.checks.signatures._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks.signatures._functions import Definition
    from py_checks.core import ParsedFile

CODE: Final = "function-length"


class FunctionLengthSettings(CheckSettings):
    max_lines: int = Field(
        default=50,
        gt=0,
    )


class FunctionLength:
    """Падает, если функция длиннее лимита.

    Функция за пределом прячет внутри себя вторую. Считается тело как
    написано — пустые строки и комментарии тоже держат в голове, — а подпись и
    декораторы нет: они описывают функцию, а не работу, которую она делает.

    Похожее правило есть у ruff, `PLR0915`, но оно считает инструкции, а не
    строки: замер на четырёх сервисах дал ноль срабатываний при пределе в
    полсотни, а самая длинная функция там — 91 строка и две инструкции.

    Настройка: `max-lines`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = FunctionLengthSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=FunctionLengthSettings,
            code=CODE,
        )
        for definition in definitions(node=file.tree):
            length = cls._length(definition=definition)
            if length <= limits.max_lines:
                continue
            yield Violation.from_node(
                node=definition.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{definition.name}: строк {length}, предел {limits.max_lines}; "
                    "вынеси часть в отдельную функцию"
                ),
            )

    @staticmethod
    def _length(*, definition: Definition) -> int:
        """Строки тела: от первой инструкции до последней строки функции.

        Подпись не считается: разложенная по столбцу, она добавила бы функции
        десяток строк, которых в ней никто не читает как работу.
        """
        node = definition.node
        end = node.end_lineno
        if end is None:
            return 0
        return end - node.body[0].lineno + 1
