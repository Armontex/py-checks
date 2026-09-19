"""Ограниченная колонка повторяет своё ограничение в базе."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks._names import name
from python_checks.checks.database._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "bound-checks"

MAPPED: Final = "Mapped"


class BoundChecksSettings(CheckSettings):
    zones: tuple[str, ...] = ()
    primitives: tuple[str, ...] = ()
    call: str = "bound_check"
    column: str = "column"
    primitive: str = "primitive"


class BoundChecks:
    """Падает, если ограниченная колонка не повторила своё ограничение как CHECK.

    Колонка, объявленная `Mapped[PositiveDecimal]`, обещает дважды. pyright
    держит каждую строку, СОБРАННУЮ здесь, значениями, которые тип пропустил;
    `bound_check(column=..., primitive=PositiveDecimal)` в `__table_args__`
    держит каждую строку, записанную любым другим способом — бэкфилл, сессия
    psql, второй сервис в следующем году. Правило связывает две половины:
    аннотация без CHECK — это база, доверяющая коду, которого она не видела.

    Проверяется наличие, а не эквивалентность, и потому ему можно верить: SQL
    генерируется из того же `BOUND`, которым отказывает тип, так что второго
    выражения для сравнения просто нет — есть вызов, который могли забыть.
    Отдельно отвергается `primitive=`, называющий не тот тип, что в аннотации:
    это единственный способ протащить расхождение обратно.

    Список ограниченных типов проектный: библиотека не может знать, что у
    этого сервиса деньги — `PositiveDecimal`, а доля — `MarginFraction`. Без
    списка правило молчит.

    Настройки: `zones`, `primitives`, `call`, `column`, `primitive`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = BoundChecksSettings
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
            model=BoundChecksSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not any(where.holds(path=zone) for zone in limits.zones):
            return
        for node in file.tree.body:
            if isinstance(node, ast.ClassDef):
                yield from cls._columns(
                    file=file,
                    node=node,
                    limits=limits,
                )

    @classmethod
    def _columns(
        cls,
        *,
        file: ParsedFile,
        node: ast.ClassDef,
        limits: BoundChecksSettings,
    ) -> Iterator[Violation]:
        declared = cls._declared(
            node=node,
            limits=limits,
        )
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if not isinstance(statement.target, ast.Name):
                continue
            bounded = cls._bounded(node=statement.annotation)
            if bounded is None or bounded not in limits.primitives:
                continue
            field = statement.target.id
            said = declared.get(field)
            if said == bounded:
                continue
            yield Violation.from_node(
                node=statement,
                path=file.path,
                code=CODE,
                message=cls._message(
                    field=field,
                    bounded=bounded,
                    said=said,
                    limits=limits,
                ),
            )

    @staticmethod
    def _message(
        *,
        field: str,
        bounded: str,
        said: str | None,
        limits: BoundChecksSettings,
    ) -> str:
        if said is None:
            return (
                f"{field} объявлено как {bounded}, но CHECK не несёт; добавь "
                f"{limits.call}({limits.column}={field}, {limits.primitive}={bounded}) "
                f"в __table_args__"
            )
        return (
            f"{field} объявлено как {bounded}, а его {limits.call} называет {said}; "
            f"аннотация и CHECK читают одну границу"
        )

    @classmethod
    def _declared(
        cls,
        *,
        node: ast.ClassDef,
        limits: BoundChecksSettings,
    ) -> dict[str, str]:
        """Колонка — тип, по каждому вызову в теле класса."""
        found: dict[str, str] = {}
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or name(node=child.func) != limits.call:
                continue
            column = cls._argument(
                node=child,
                named=limits.column,
            )
            primitive = cls._argument(
                node=child,
                named=limits.primitive,
            )
            if column is not None and primitive is not None:
                found[column] = primitive
        return found

    @staticmethod
    def _argument(
        *,
        node: ast.Call,
        named: str,
    ) -> str | None:
        for keyword in node.keywords:
            if keyword.arg == named and isinstance(keyword.value, ast.Name):
                return keyword.value.id
        return None

    @staticmethod
    def _bounded(*, node: ast.expr) -> str | None:
        """X из `Mapped[X]` или `Mapped[X | None]`, если это простое имя."""
        if not isinstance(node, ast.Subscript) or name(node=node.value) != MAPPED:
            return None
        match node.slice:
            case ast.Name(id=inside):
                return inside
            case ast.BinOp(left=ast.Name(id=inside), op=ast.BitOr()):
                return inside
            case _:
                return None
