"""A dataclass is declared so that a value stays a value."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import name
from py_checks.checks.types._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "frozen-dataclasses"

DECORATOR: Final = "dataclass"


class FrozenDataclassesSettings(ZonedSettings):
    options: tuple[str, ...] = ("frozen", "slots", "kw_only")


class FrozenDataclasses:
    """Fails when a dataclass in a zone is declared without the required arguments.

    A thing of the business is a value: assembled once and not changed, so an
    existing object cannot quietly slide into a state that is not allowed.
    `frozen` buys that, `slots` keeps a typo from inventing an attribute nobody
    declared, and `kw_only` keeps two fields of the same type from swapping
    places: in a value of four strings only the author remembers the order.

        @dataclass(frozen=True, slots=True, kw_only=True)
        class Price: ...

    The zone is the project's: keeping values immutable makes sense where the
    rules live, not in the config and not in the wiring. Without zones the rule
    stays silent.

    Settings: `zones`, `options`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = FrozenDataclassesSettings
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
            model=FrozenDataclassesSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            decorator = cls._decorator(node=node)
            if decorator is None:
                continue
            missing = tuple(
                option for option in limits.options if option not in cls._enabled(node=decorator)
            )
            if not missing:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    f"dataclass {node.name} is declared without "
                    f"{', '.join(f'{option}=True' for option in missing)}"
                ),
            )

    @staticmethod
    def _decorator(*, node: ast.ClassDef) -> ast.expr | None:
        """The `@dataclass` decorator, with arguments or without."""
        for item in node.decorator_list:
            called = item.func if isinstance(item, ast.Call) else item
            if name(node=called) == DECORATOR:
                return item
        return None

    @classmethod
    def _enabled(cls, *, node: ast.expr) -> frozenset[str]:
        """The decorator's arguments set to `True`."""
        if not isinstance(node, ast.Call):
            return frozenset()
        return frozenset(
            keyword.arg
            for keyword in node.keywords
            if keyword.arg is not None and cls._true(node=keyword.value)
        )

    @staticmethod
    def _true(*, node: ast.expr) -> bool:
        return isinstance(node, ast.Constant) and node.value is True
