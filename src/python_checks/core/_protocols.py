"""Каким библиотека видит правило."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from python_checks.config import CheckSettings
    from python_checks.core._source import ParsedFile
    from python_checks.core._violation import Violation


class Scope(StrEnum):
    """Что правилу дают на суд.

    Вид объявляет само правило, а не группа entry points: так автор чужого
    пакета пишет одну запись, а `list` и `explain` видят все правила разом, не
    складывая два реестра в один.
    """

    # Один файл, разобранный ядром: таких правил большинство.
    FILE = "file"

    # Корень проекта: манифест, согласие двух файлов репозитория между собой.
    PROJECT = "project"

    # То же, что `PROJECT`, но правилу нужна живая среда — база, сеть, долгий
    # прогон. В обычный прогон такое не входит: его зовут по имени или в CI,
    # иначе хук на коммит начинает ждать базу.
    ENVIRONMENT = "environment"


@runtime_checkable
class FileCheck(Protocol):
    """Правило, которому хватает одного файла.

    Всё остальное — поиск файлов, разбор, настройки, вывод — делает ядро.
    Проверка знает только своё условие и возвращает нарушения, ничего не
    печатая: иначе формат вывода расползётся по сорока правилам.
    """

    code: ClassVar[str]
    Settings: ClassVar[type[CheckSettings]]
    scope: ClassVar[Scope]

    # Слово группы, к которой правило принадлежит: `# signature-ok` снимает
    # любую проверку из `signatures`. Пишется один раз на пакет, потому что
    # человек помнит группу («это про подписи»), а не сорок кодов. Канонический
    # `# check-ok: <код>` работает всегда и снимает ровно одно правило.
    marker: ClassVar[str]

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

    code: ClassVar[str]
    Settings: ClassVar[type[CheckSettings]]
    scope: ClassVar[Scope]
    marker: ClassVar[str]

    def run(
        self,
        *,
        root: Path,
        settings: CheckSettings,
    ) -> Iterator[Violation]: ...


# Правило — это одно из двух: судящее файл или судящее проект. Там, где важно
# лишь то, что у него есть код и описание (список, объяснение), годится любое.
type Check = FileCheck | ProjectCheck
