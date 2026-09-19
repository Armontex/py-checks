"""Тип, которому не место в этой части дерева."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks.types._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.checks._location import Place
    from python_checks.core import ParsedFile

CODE: Final = "confined-types"

# Имя, которое говорит, что значение принадлежит классу, а не экземпляру:
# такое поле — не состояние, переходящее границу, и правило его не касается.
ASIDE: Final[frozenset[str]] = frozenset({"ClassVar", "Final"})


class ConfinedTypesSettings(CheckSettings):
    zones: dict[str, tuple[str, ...]] = {}


class ConfinedTypes:
    """Падает, если поле в этой части дерева объявлено запрещённым здесь типом.

    Одно правило на два случая, которые раньше писались по отдельности.
    `float` в домене: двоичная плавающая точка не держит цену, а ошибка
    округления в хранимом состоянии — это деньги, которые перестают сходиться.
    Голые `str`, `int`, `Decimal` там, где живут контракты: `int` говорит, что
    версия может быть −10000, `str` — что тег может быть пустым, `Decimal` —
    что коэффициент может быть отрицательным или NaN. Ничего из этого про дело
    не верно, а тип — последнее место, где это можно сказать один раз, а не
    перепроверять глазами.

    Какие типы где запрещены — дело проекта: в одном сервисе деньги считают
    везде, в другом `float` в отчёте законен. Без таблицы правило молчит.

    Аннотация просматривается насквозь: `tuple[str, ...]` — та же голая строка
    этажом ниже. Судятся поля класса; `ClassVar` и `Final` — не поля: они
    принадлежат классу, а не экземпляру.

    Настройка: `zones` — путь (можно с `*`: `modules/*/domain`) и список имён.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfinedTypesSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        zones = settings_as(
            settings=settings,
            model=ConfinedTypesSettings,
            code=CODE,
        ).zones
        where = place(file=file)
        if where is None:
            return
        forbidden = cls._forbidden(
            where=where,
            zones=zones,
        )
        if not forbidden:
            return
        for name, statement in cls._fields(tree=file.tree):
            found = cls._named(node=statement.annotation) & forbidden
            if not found:
                continue
            yield Violation.from_node(
                node=statement,
                path=file.path,
                code=CODE,
                message=(
                    f"{name} объявлено через {', '.join(sorted(found))}; "
                    f"здесь тип называет, что значение может держать"
                ),
            )

    @staticmethod
    def _forbidden(
        *,
        where: Place,
        zones: dict[str, tuple[str, ...]],
    ) -> frozenset[str]:
        """Всё, что запрещено в этом месте: зоны складываются, а не спорят."""
        return frozenset(
            name for zone, names in zones.items() if where.holds(path=zone) for name in names
        )

    @classmethod
    def _fields(cls, *, tree: ast.Module) -> Iterator[tuple[str, ast.AnnAssign]]:
        """Поля классов модуля под именами вида `Класс.поле`."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for statement in node.body:
                if not isinstance(statement, ast.AnnAssign):
                    continue
                if not isinstance(statement.target, ast.Name):
                    continue
                if cls._named(node=statement.annotation) & ASIDE:
                    continue
                yield f"{node.name}.{statement.target.id}", statement

    @staticmethod
    def _named(*, node: ast.expr) -> frozenset[str]:
        """Имена, написанные внутри аннотации, на любой глубине."""
        return frozenset(
            child.id if isinstance(child, ast.Name) else child.attr
            for child in ast.walk(node)
            if isinstance(child, ast.Name | ast.Attribute)
        )
