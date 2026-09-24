"""A type that does not belong in this part of the tree."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import place
from py_checks.checks._names import walked
from py_checks.checks.types._marker import MARKER
from py_checks.config import OPEN, CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks._location import Place
    from py_checks.core import ParsedFile

CODE: Final = "confined-types"

# A name that says the value belongs to the class rather than to an instance:
# such a field is not state crossing a boundary, and not the rule's business.
ASIDE: Final[frozenset[str]] = frozenset({"ClassVar", "Final"})


class ConfinedTypesSettings(CheckSettings):
    """The `[confined-types]` section: an address and the types never found there.

    The keys come from the project, so there is no sub-table: the directory
    name is the setting itself, not a value under its name.
    """

    model_config = OPEN

    __pydantic_extra__: dict[str, tuple[str, ...]]  # type: ignore[assignment]

    @property
    def forbidden(self) -> dict[str, tuple[str, ...]]:
        return self.__pydantic_extra__


class ConfinedTypes:
    """Fails when a field in this part of the tree is declared with a type banned here.

    One rule for two cases that used to be written separately. `float` in the
    domain: binary floating point does not hold a price, and a rounding error
    in stored state is money that stops adding up. Bare `str`, `int`,
    `Decimal` where the contracts live: `int` says the version may be −10000,
    `str` that the tag may be empty, `Decimal` that the coefficient may be
    negative or NaN. None of that is true of the business, and the type is the
    last place where it can be said once instead of re-checked by eye.

    Which types are banned where is the project's call: one service counts
    money everywhere, in another a `float` in a report is lawful. Without the
    table the rule stays silent.

    An annotation is seen through: `tuple[str, ...]` is the same bare string
    one floor down. Class fields are judged; `ClassVar` and `Final` are not
    fields: they belong to the class rather than to an instance.

    Settings: an address (`*` allowed: `modules/*/domain`) and a list of names.
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
        ).forbidden
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
            found = frozenset(walked(node=statement.annotation)) & forbidden
            if not found:
                continue
            yield Violation.from_node(
                node=statement,
                path=file.path,
                code=CODE,
                message=(
                    f"{name} is declared with {', '.join(sorted(found))}; "
                    f"here the type names what the value may hold"
                ),
            )

    @staticmethod
    def _forbidden(
        *,
        where: Place,
        zones: dict[str, tuple[str, ...]],
    ) -> frozenset[str]:
        """Everything banned in this place: zones add up rather than compete."""
        return frozenset(
            name for zone, names in zones.items() if where.holds(path=zone) for name in names
        )

    @staticmethod
    def _fields(*, tree: ast.Module) -> Iterator[tuple[str, ast.AnnAssign]]:
        """The module's class fields, named as `Class.field`."""
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for statement in node.body:
                if not isinstance(statement, ast.AnnAssign):
                    continue
                if not isinstance(statement.target, ast.Name):
                    continue
                if frozenset(walked(node=statement.annotation)) & ASIDE:
                    continue
                yield f"{node.name}.{statement.target.id}", statement
