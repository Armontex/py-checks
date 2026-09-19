"""Каким библиотека видит правило."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

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

    # Слово группы, к которой правило принадлежит: `# signature-ok` снимает
    # любую проверку из `signatures`. Пишется один раз на пакет, потому что
    # человек помнит группу («это про подписи»), а не сорок кодов. Канонический
    # `# check-ok: <код>` работает всегда и снимает ровно одно правило.
    marker: str

    def run(
        self,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]: ...


@runtime_checkable
class ProjectCheck(Protocol):
    """Правило, которому одного файла мало.

    Манифест зависимостей, согласие двух файлов репозитория между собой — то,
    что живёт не в исходнике, а в проекте. Такое правило вызывается один раз за
    прогон и само решает, что ему прочитать; ядро даёт ему корень и настройки.
    """

    code: str
    Settings: type[CheckSettings]
    marker: str

    def run(
        self,
        *,
        root: Path,
        settings: CheckSettings,
    ) -> Iterator[Violation]: ...


# Правило — это одно из двух: судящее файл или судящее проект. Там, где важно
# лишь то, что у него есть код и описание (список, объяснение), годится любое.
type Check = FileCheck | ProjectCheck
