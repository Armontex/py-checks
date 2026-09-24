"""No foreign package inside a sealed zone."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import place
from py_checks.checks.imports._marker import MARKER
from py_checks.checks.imports._statements import imports
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks._location import Place
    from py_checks.core import ParsedFile

CODE: Final = "sealed-imports"


class SealedSettings(CheckSettings):
    zones: tuple[str, ...] = ()
    allow: dict[str, tuple[str, ...]] = {}


class SealedImports:
    """Fails when a sealed zone imports a foreign package.

    The rules and the interfaces around them know nothing but the standard
    library and the service's own code: a DTO here is a dataclass, not a
    framework's model. The list is an allow list, not a deny list, because
    otherwise every new framework gets inside in silence.

    Permissions are given per layer, not for the whole zone: the layer that
    leads usually has the right to say what happened, and the layer with the
    rules knows nothing.

    The project knows which zones are sealed: the library cannot guess what it
    calls `modules`. Without `zones` the rule stays silent.

    Settings: `zones`, `allow`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = SealedSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        own = settings_as(
            settings=settings,
            model=SealedSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not where.inside(zones=own.zones):
            return
        allowed = cls._allowed(
            where=where,
            allow=own.allow,
        )
        for imported in imports(tree=file.tree):
            if imported.stdlib or imported.top in {where.package, *allowed}:
                continue
            yield Violation.from_node(
                node=imported.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{imported.top} in {where.where}: a sealed zone knows only "
                    "the standard library and the service's own code"
                ),
            )

    @staticmethod
    def _allowed(
        *,
        where: Place,
        allow: dict[str, tuple[str, ...]],
    ) -> frozenset[str]:
        """What this layer may import: a file has one zone, but its own layer inside it."""
        return frozenset(package for part in where.directories for package in allow.get(part, ()))
