"""A bounded column restates its bound in the database."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from pydantic import Field

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import name
from py_checks.checks.database._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "bound-checks"

MAPPED: Final = "Mapped"


class Helper(CheckSettings):
    """What the project's helper and its two arguments are called.

    Three bare words in the section did not say they belonged together: `call`
    is the function, `column` and `primitive` are its arguments, and that could
    only be read from the documentation. A block says it by its shape.
    """

    call: str = "bound_check"
    column: str = "column"
    primitive: str = "primitive"


class BoundChecksSettings(ZonedSettings):
    primitives: tuple[str, ...] = ()
    helper: Helper = Field(default_factory=Helper)


class BoundChecks:
    """Fails if a bounded column did not restate its bound as a CHECK.

    A column declared `Mapped[PositiveDecimal]` promises twice. pyright holds
    every row BUILT here to values the type let through;
    `bound_check(column=..., primitive=PositiveDecimal)` in `__table_args__`
    holds every row written any other way — a backfill, a psql session, a
    second service next year. The rule ties the two halves together: an
    annotation without a CHECK is a database trusting code it has never seen.

    Presence is checked rather than equivalence, and that is why it can be
    trusted: the SQL is generated from the same `BOUND` the type refuses by, so
    there is no second expression to compare against — there is a call
    somebody may have forgotten. Separately refused is a `primitive=` naming a
    type other than the one in the annotation: that is the only way to smuggle
    the disagreement back in.

    The list of bounded types is the project's: the library cannot know that
    money in this service is `PositiveDecimal` and a share is
    `MarginFraction`. Without the list the rule is silent.

    Settings: `zones`, `primitives`, `helper`.
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
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
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
        helper = limits.helper
        if said is None:
            return (
                f"{field} is declared as {bounded} but carries no CHECK; add "
                f"{helper.call}({helper.column}={field}, {helper.primitive}={bounded}) "
                f"to __table_args__"
            )
        return (
            f"{field} is declared as {bounded}, but its {helper.call} names {said}; "
            f"the annotation and the CHECK read one bound"
        )

    @classmethod
    def _declared(
        cls,
        *,
        node: ast.ClassDef,
        limits: BoundChecksSettings,
    ) -> dict[str, str]:
        """Column to type, one per call in the class body."""
        found: dict[str, str] = {}
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or name(node=child.func) != limits.helper.call:
                continue
            column = cls._argument(
                node=child,
                named=limits.helper.column,
            )
            primitive = cls._argument(
                node=child,
                named=limits.helper.primitive,
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
        """X from `Mapped[X]` or `Mapped[X | None]`, if it is a plain name."""
        if not isinstance(node, ast.Subscript) or name(node=node.value) != MAPPED:
            return None
        match node.slice:
            case ast.Name(id=inside):
                return inside
            case ast.BinOp(left=ast.Name(id=inside), op=ast.BitOr()):
                return inside
            case _:
                return None
