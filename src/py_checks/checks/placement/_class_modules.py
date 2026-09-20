"""Директория объявляет, что в ней живёт."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._kind import declarations
from py_checks.checks._layout import SECTION, Layout, innermost
from py_checks.checks._location import place
from py_checks.checks.placement._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "class-modules"


class ClassModules:
    """Падает, если в модуле лежит то, чего его директория не допускает.

    Директория называет, что в ней живёт, и рядом не садится ничего другого.
    Хелпер, заехавший в модуль use case, — либо часть класса, и тогда он
    статический метод внутри, либо общий, и тогда ему место там, где лежит
    остальное общее. Перечисление, забредшее в `dto/`, — та же история.

    Импорты, константы, блоки `if TYPE_CHECKING` и докстринг разрешены везде:
    правило про то, что модуль объявляет, а не про то, чем он пользуется.

    Адрес в заголовке блока — путь, а не имя директории, и это важно:
    `application/services` держит класс-оркестратор, а `domain/services` —
    функции, правила, сравнивающие два факта. Одно слово, два разных зверя.
    Директории, о которой раскладка молчит, правило не касается.

    Настройка: `only` в общей таблице `[layout]`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = Layout
    section: ClassVar[str] = SECTION
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        layout = settings_as(
            settings=settings,
            model=Layout,
            code=CODE,
        ).directories
        where = place(file=file)
        if where is None:
            return
        found = innermost(
            where=where,
            among=[(address, directory) for address, directory in layout.items() if directory.only],
        )
        if found is None:
            return
        address, directory = found
        for declared in declarations(tree=file.tree):
            # Вид не виден — судить не о чем: это класс с базой из другого модуля.
            if declared.kind is None or declared.kind in directory.only:
                continue
            yield Violation.from_node(
                node=declared.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{declared.name} — {declared.kind.said}; в {address} держат "
                    f"{', '.join(sorted(one.said for one in directory.only))}"
                ),
            )
