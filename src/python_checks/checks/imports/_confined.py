"""Пакет живёт там, где ему место."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks.imports._marker import MARKER
from python_checks.checks.imports._statements import imports
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from python_checks.checks._location import Place
    from python_checks.checks.imports._statements import Imported
    from python_checks.core import ParsedFile

CODE: Final = "confined-imports"


class ConfinedSettings(CheckSettings):
    packages: dict[str, tuple[str, ...]] = {}


class ConfinedImports:
    """Падает, если пакет импортируется вне отведённых ему мест.

    Фреймворк, расползшийся по всем слоям, — это фреймворк, который нельзя
    заменить: замена превращается в правку всего сервиса. Пока ORM живёт в
    `infra/database`, а веб-стек на краю, каждый из них меняется в одном месте.

    Где чьё место, знает проект: у сервиса это `infra/database`, у утилиты
    такого слоя нет вовсе. Список пишется в
    `[tool.python-checks.confined-imports.packages]`; пустой список значит
    «нигде» — так держат убранную библиотеку, чтобы она не вернулась. Пакета,
    которого в списке нет, правило не касается.

    Настройка: `packages`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfinedSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(cls, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        table = settings_as(settings=settings, model=ConfinedSettings, code=CODE).packages
        where = place(file=file)
        if where is None:
            return
        for imported in imports(tree=file.tree):
            allowed = table.get(imported.top)
            if allowed is None or any(where.under(prefix=path) for path in allowed):
                continue
            yield cls._violation(imported=imported, where=where, allowed=allowed, path=file.path)

    @staticmethod
    def _violation(
        *,
        imported: Imported,
        where: Place,
        allowed: tuple[str, ...],
        path: Path,
    ) -> Violation:
        message = (
            f"{imported.top} в {where.where}; ему место в {', '.join(allowed)}"
            if allowed
            else f"{imported.top} в {where.where}; этот пакет убран, импортировать его негде"
        )
        return Violation.from_node(node=imported.node, path=path, code=CODE, message=message)
