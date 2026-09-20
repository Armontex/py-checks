"""Класс лежит там, где лежат классы его вида."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._kind import declarations
from py_checks.checks._layout import SECTION, Layout, claimants
from py_checks.checks._location import place
from py_checks.checks.placement._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "class-placement"


class ClassPlacement:
    """Падает, если класс лежит не там, где лежат классы его вида.

    Директория называет вид, и читатель находит порт, не открывая файла.
    Дом объявляется в раскладке: `home` — про вид объявления, `suffix` — про
    имя. Адресов у одного вида может быть несколько, и тогда дом — любой из
    них: порт репозитория и его реализация законно лежат в двух местах, а
    словарь отказов — и в `errors/`, и в `exceptions.py`.

    Вид, о котором раскладка не сказала ни слова, правилу не подсуден: пока
    `dataclass` не назвал своего дома, он лежит где угодно. Назвал — значит
    перечислены все дома, в том числе доменный: value object тоже dataclass.

    `area` сужает притязание до части дерева: соглашение про `dto` написано
    про слой приложения, а dataclass в загрузчике или в наблюдаемости — это
    способ сложить три поля рядом, а не предмет разговора.

    Настройки: `home`, `suffix` и `area` в общей таблице `[layout]`.
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
        for declared in declarations(tree=file.tree):
            homes = claimants(
                declared=declared,
                layout=layout,
                where=where,
            )
            if not homes or any(where.holds(path=home.address) for home in homes):
                continue
            yield Violation.from_node(
                node=declared.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{declared.name} {homes[0].said}; "
                    f"ему место в {', '.join(home.address for home in homes)}"
                ),
            )
