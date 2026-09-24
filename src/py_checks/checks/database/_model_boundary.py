"""An ORM model does not leave the layer that understands it."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._layout import SECTION, Layout, Orm, addressed
from py_checks.checks._location import place
from py_checks.checks._names import name, walked
from py_checks.checks.database._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks._layout import Directory
    from py_checks.checks._location import Place
    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "model-boundary"

PRIVATE: Final = "_"
DOT: Final = "."
SEPARATOR: Final = "/"

# What the models' base class is called, unless the home says otherwise.
BASE: Final = "Base"


@dataclass(frozen=True, slots=True)
class Boundary:
    """The two ends of the agreement about a model, read from the layout."""

    declared: tuple[str, ...]
    built: tuple[str, ...]
    base: str


class ModelBoundary:
    """Fails if an ORM model is declared, built or handed out in the wrong place.

    A model is a description of a table, and three rules keep it one.

    It is declared where models are declared: anywhere else it is a table
    nobody expects at that address, and alembic's autogenerate sees only the
    models the imports of their package reach.

    It is built only in repositories: to build a model is to write a row, and
    a model built anywhere else either does nothing — nobody outside holds a
    session to add it to — or it is a row written by a layer with no
    transaction to write it in.

    A repository's public method does not return it. A model carries the
    session with it: touching an attribute after the transaction closed either
    fails or goes to the database from a layer that may not, and half the
    schema is reachable from there by relationships — a query leaving code
    that never asked for a connection. Repositories return DTOs, identifiers,
    counts — everything the database layer has finished with.

    A model is recognised in two ways, both visible in one file: declaration
    by the `Base` parent, use by the import from the models package. The name
    has nothing to do with it: `SettingsModel` in the settings and
    `DeviceModel` in the domain are not tables.

    Settings: `orm` in the shared `[layout]` table — `"declared"` on the
    models' home and `"built"` where they are built; `base` next to the home,
    if the base class is not called `Base`.
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
        limits = cls._boundary(
            layout=settings_as(
                settings=settings,
                model=Layout,
                code=CODE,
            ).directories
        )
        where = place(file=file)
        if where is None or not limits.declared:
            return
        models = cls._models(
            file=file,
            limits=limits,
        )
        found = [
            *cls._declared(
                file=file,
                where=where,
                limits=limits,
            ),
            *cls._built(
                file=file,
                where=where,
                limits=limits,
                models=models,
            ),
            *cls._returned(
                file=file,
                where=where,
                limits=limits,
                models=models,
            ),
        ]
        yield from sorted(found, key=lambda violation: (violation.line, violation.column))

    @staticmethod
    def _boundary(*, layout: dict[str, Directory]) -> Boundary:
        """The models' home, where they are built, the base's name — all from the layout."""
        declared = addressed(
            layout=layout,
            orm=Orm.DECLARED,
        )
        named = next(
            (layout[address].base for address in declared if layout[address].base is not None),
            None,
        )
        return Boundary(
            declared=declared,
            built=addressed(
                layout=layout,
                orm=Orm.BUILT,
            ),
            base=named or BASE,
        )

    @classmethod
    def _declared(
        cls,
        *,
        file: ParsedFile,
        where: Place,
        limits: Boundary,
    ) -> Iterator[Violation]:
        """A model declared outside the models' home."""
        if where.anywhere(
            zones=limits.declared,
        ):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            if any(name(node=base) == limits.base for base in node.bases):
                yield Violation.from_node(
                    node=node,
                    path=file.path,
                    code=CODE,
                    message=(
                        f"{node.name} is declared outside {', '.join(limits.declared)}; "
                        f"autogenerate sees only the models of their package"
                    ),
                    end_line=node.body[0].lineno,
                )

    @classmethod
    def _built(
        cls,
        *,
        file: ParsedFile,
        where: Place,
        limits: Boundary,
        models: frozenset[str],
    ) -> Iterator[Violation]:
        """A model built where there is nothing to write the row with."""
        if where.anywhere(
            zones=limits.built + limits.declared,
        ):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            built = name(node=node.func)
            if built in models:
                yield Violation.from_node(
                    node=node,
                    path=file.path,
                    code=CODE,
                    message=(
                        f"{built}(...) is built outside {', '.join(limits.built)}; "
                        f"to build a model is to write a row"
                    ),
                )

    @classmethod
    def _returned(
        cls,
        *,
        file: ParsedFile,
        where: Place,
        limits: Boundary,
        models: frozenset[str],
    ) -> Iterator[Violation]:
        """A model handed out by a repository's public method."""
        if not where.anywhere(
            zones=limits.built,
        ):
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if node.name.startswith(PRIVATE) or node.returns is None:
                continue
            returned = cls._named(
                node=node.returns,
                models=models,
            )
            if returned is None:
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=(
                    f"{node.name} returns {returned}; a model carries the session with it — "
                    f"return a DTO, an identifier, a count"
                ),
                end_line=node.body[0].lineno,
            )

    @classmethod
    def _models(
        cls,
        *,
        file: ParsedFile,
        limits: Boundary,
    ) -> frozenset[str]:
        """Names imported from the models package."""
        names: set[str] = set()
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.ImportFrom) or node.module is None:
                continue
            if cls._home(
                module=node.module,
                zones=limits.declared,
            ):
                names.update(alias.asname or alias.name for alias in node.names)
        return frozenset(names)

    @staticmethod
    def _home(
        *,
        module: str,
        zones: tuple[str, ...],
    ) -> bool:
        path = SEPARATOR.join(module.split(DOT))
        return any(
            f"{SEPARATOR}{zone}{SEPARATOR}" in f"{SEPARATOR}{path}{SEPARATOR}" for zone in zones
        )

    @staticmethod
    def _named(
        *,
        node: ast.expr,
        models: frozenset[str],
    ) -> str | None:
        """A model's name, named anywhere inside the annotation."""
        return next((found for found in walked(node=node) if found in models), None)
