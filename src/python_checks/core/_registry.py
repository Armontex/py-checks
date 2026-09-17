"""Какие проверки существуют и как их находят."""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.config import CheckSettings
    from python_checks.core._source import ParsedFile
    from python_checks.core._violation import Violation

GROUP = "python_checks.checks"


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


class UnknownCheckError(Exception):
    """Такой проверки нет."""

    def __init__(self, code: str, known: tuple[str, ...]) -> None:
        super().__init__(f"неизвестная проверка {code!r}; есть: {', '.join(known)}")
        self.code = code


def available() -> dict[str, FileCheck]:
    """Все проверки, объявленные через entry points.

    Так проект или команда добавляет своё правило: ставит рядом свой пакет с
    записью в этой же группе, а библиотеку форкать не нужно.
    """
    found: dict[str, FileCheck] = {}
    for entry in entry_points(group=GROUP):
        check = entry.load()()
        found[check.code] = check
    return found


def get(code: str) -> FileCheck:
    checks = available()
    if code not in checks:
        raise UnknownCheckError(code, tuple(sorted(checks)))
    return checks[code]
