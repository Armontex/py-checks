"""What a model's column is built out of."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import name
from py_checks.checks.database._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "model-columns"

MAPPED: Final = "Mapped"
AWARE: Final = "timezone"
NULLABLE: Final = "nullable"


class ModelColumnsSettings(ZonedSettings):
    factories: tuple[str, ...] = ("mapped_column", "Column")
    instead: dict[str, str] = {}
    wrappers: dict[str, str] = {}
    defaults: tuple[str, ...] = ()
    skip: tuple[str, ...] = ()
    aware: tuple[str, ...] = ()
    nullable: bool = True


class ModelColumns:
    """Fails if a column is built out of the wrong material.

    Five rules on one table of settings.

    `instead` is the material that has no place in a column, and what to write
    instead. A bare `Enum` is a native Postgres type: every new member needs an
    `ALTER TYPE`, and these vocabularies belong to somebody else and will grow.
    `Float` does not hold a price exactly, and a column is state: the rounding
    error accumulates with every write. A bare `JSONB` is a shape nobody
    declared: what the writer put in is what every reader gets, and the
    parsing that would have caught a missing key happens in each of them
    separately or nowhere.

    `wrappers` is the module allowed to name that material: the wrapper over it
    lives there, and the rule leaves it alone.

    `defaults` lists every way a column fills itself in. A default is a value
    nobody wrote: the writer skipped the column, the row got a number anyway,
    and an omission that a type checker would have caught on a missing
    constructor argument turns into a plausible row.

    `skip` lists the built-in types in `Mapped[...]`. Such a column says what
    kind of value it holds and nothing about which values are allowed, so every
    writer has to remember the rule.

    `aware` lists the time types that need `timezone=True`: without it the
    column stores a naive stamp — the writer's own wall clock, unsigned.

    `nullable`: the annotation and the keyword must agree. SQLAlchemy lets them
    diverge, and then the annotation lies: pyright reasons by it, the database
    holds the keyword, and one of the two is wrong on every row.

    Settings: `zones`, `factories`, `instead`, `wrappers`, `defaults`, `skip`,
    `aware`, `nullable`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ModelColumnsSettings
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
            model=ModelColumnsSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
            return
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Call):
                yield from cls._material(
                    file=file,
                    node=node,
                    limits=limits,
                )
            if isinstance(node, ast.AnnAssign):
                yield from cls._annotation(
                    file=file,
                    node=node,
                    limits=limits,
                )

    @classmethod
    def _material(
        cls,
        *,
        file: ParsedFile,
        node: ast.Call,
        limits: ModelColumnsSettings,
    ) -> Iterator[Violation]:
        """The material, and whatever the column fills itself in with."""
        written = name(node=node.func)
        if written in limits.instead and limits.wrappers.get(written) != file.path.stem:
            yield cls._says(
                file=file,
                node=node,
                message=limits.instead[written],
            )
        if written in limits.aware and not cls._said(
            node=node,
            named=AWARE,
        ):
            yield cls._says(
                file=file,
                node=node,
                message=(
                    f"{written} without timezone=True stores a naive timestamp; say timezone=True"
                ),
            )
        if written not in limits.factories:
            return
        for keyword in node.keywords:
            if keyword.arg in limits.defaults:
                yield cls._says(
                    file=file,
                    node=node,
                    message=(
                        f"{keyword.arg}= fills the column in for a writer who did not write it; "
                        f"pass the value in the statement"
                    ),
                )

    @classmethod
    def _annotation(
        cls,
        *,
        file: ParsedFile,
        node: ast.AnnAssign,
        limits: ModelColumnsSettings,
    ) -> Iterator[Violation]:
        """The column's annotation: a built-in type, and agreement with `nullable=`."""
        inner = cls._mapped(node=node.annotation)
        if inner is None:
            return
        written, optional = inner
        if written in limits.skip:
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(f"{written} says a kind, not a rule; take a primitive with its bound"),
            )
        if not limits.nullable:
            return
        said = cls._nullable(
            node=node.value,
            limits=limits,
        )
        if said is not None and said != optional:
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    "the annotation and nullable= disagree; at run time the one the type "
                    "checker cannot see wins"
                ),
            )

    @staticmethod
    def _nullable(
        *,
        node: ast.expr | None,
        limits: ModelColumnsSettings,
    ) -> bool | None:
        """What `nullable=` says, if it says anything."""
        if not isinstance(node, ast.Call) or name(node=node.func) not in limits.factories:
            return None
        for keyword in node.keywords:
            if keyword.arg == NULLABLE and isinstance(keyword.value, ast.Constant):
                return bool(keyword.value.value)
        return None

    @classmethod
    def _mapped(cls, *, node: ast.expr) -> tuple[str, bool] | None:
        """The name inside `Mapped[...]`, and whether it allows `None`."""
        if not isinstance(node, ast.Subscript) or name(node=node.value) != MAPPED:
            return None
        match node.slice:
            case ast.Name(id=inside) | ast.Attribute(attr=inside):
                return inside, False
            case ast.BinOp(left=ast.Name(id=inside), op=ast.BitOr(), right=right):
                return inside, cls._none(node=right)
            case _:
                return None

    @staticmethod
    def _none(*, node: ast.expr) -> bool:
        return isinstance(node, ast.Constant) and node.value is None

    @staticmethod
    def _said(
        *,
        node: ast.Call,
        named: str,
    ) -> bool:
        return any(
            keyword.arg == named and keyword.value != ast.Constant(value=False)
            for keyword in node.keywords
        )

    @staticmethod
    def _says(
        *,
        file: ParsedFile,
        node: ast.Call,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=node,
            path=file.path,
            code=CODE,
            message=message,
        )
