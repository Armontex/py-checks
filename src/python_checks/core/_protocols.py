"""Каким библиотека видит правило."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.config import CheckSettings
    from python_checks.core._source import ParsedFile
    from python_checks.core._violation import Violation


@runtime_checkable
class FileCheck(Protocol):
    """Правило, которому хватает одного файла.

    Всё остальное — поиск файлов, разбор, настройки, вывод — делает ядро.
    Проверка знает только своё условие и возвращает нарушения, ничего не
    печатая: иначе формат вывода расползётся по сорока правилам.
    """

    code: str
    Settings: type[CheckSettings]

    def run(self, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]: ...
