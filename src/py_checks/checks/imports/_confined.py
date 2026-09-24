"""A package lives where it belongs."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import place
from py_checks.checks.imports._marker import MARKER
from py_checks.checks.imports._statements import imports
from py_checks.config import OPEN, CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from py_checks.checks._location import Place
    from py_checks.checks.imports._statements import Imported
    from py_checks.core import ParsedFile

CODE: Final = "confined-imports"


class ConfinedSettings(CheckSettings):
    """The `[confined-imports]` section: a package and the places it may be called from."""

    model_config = OPEN

    __pydantic_extra__: dict[str, tuple[str, ...]]  # type: ignore[assignment]

    @property
    def packages(self) -> dict[str, tuple[str, ...]]:
        return self.__pydantic_extra__


class ConfinedImports:
    """Fails when a package is imported outside the places set aside for it.

    A framework that has spread through every layer is a framework that cannot
    be replaced: the replacement becomes an edit of the whole service. While
    the ORM lives in `infra/database` and the web stack at the edge, each of
    them changes in one place.

    The project knows what belongs where: a service has `infra/database`, a
    command-line utility has no such layer at all. The package name is the key
    in the section, the value is the places it may be; an empty list means
    "nowhere" — that is how a library that was taken out is kept out. A
    package not in the section is not the rule's business.

    Settings: package name — list of places.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfinedSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        table = settings_as(
            settings=settings,
            model=ConfinedSettings,
            code=CODE,
        ).packages
        where = place(file=file)
        if where is None:
            return
        for imported in imports(tree=file.tree):
            allowed = table.get(imported.top)
            if allowed is None or any(where.under(prefix=path) for path in allowed):
                continue
            yield cls._violation(
                imported=imported,
                where=where,
                allowed=allowed,
                path=file.path,
            )

    @staticmethod
    def _violation(
        *,
        imported: Imported,
        where: Place,
        allowed: tuple[str, ...],
        path: Path,
    ) -> Violation:
        message = (
            f"{imported.top} in {where.where}; it belongs in {', '.join(allowed)}"
            if allowed
            else f"{imported.top} in {where.where}; the package was taken out, it belongs nowhere"
        )
        return Violation.from_node(
            node=imported.node,
            path=path,
            code=CODE,
            message=message,
        )
