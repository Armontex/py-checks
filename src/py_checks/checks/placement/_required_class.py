"""A module declares the class its directory exists for."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._kind import Kind, declarations
from py_checks.checks._layout import SECTION, Layout, innermost
from py_checks.checks._location import place
from py_checks.checks.placement._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks._kind import Declaration
    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "required-class"

# The kinds of declaration allowed to stand above the required class. An alias
# and an enum are vocabulary, not a second subject: a class body executes at
# declaration time, so the names the required class uses inside itself cannot
# be written below it.
VOCABULARY: Final[frozenset[Kind]] = frozenset({Kind.ALIAS, Kind.ENUM})


class RequiredClass:
    """Fails when a module did not declare the class its directory exists for.

    A file in `use_cases` exists for a use case, a file in `repositories` for
    a repository, a file in `config` for a group of settings. A module that
    declared something else is either misnamed or in the wrong place.

    The class comes first and comes alone. First, because a reader who opens
    `repositories/order.py` is looking for the repository, and a helper above
    it reads as something more important. Alone, because the file name is how
    the reader finds the class: three use cases in one module answer the
    question "where is `ResolveLimitsUseCase`" with "read all three".

    Constants, aliases and enums are allowed above the required class: a name
    is read where it is used, and a value does not become a second subject.

    `__init__.py` re-exports rather than declares; an empty module has not
    promised anything yet; a module with a leading underscore (`_base.py`)
    holds its directory's machinery, not one of its classes. The rule leaves
    these three alone.

    Settings: `required` and `suffix` in the shared `[layout]` table.
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
        if where is None or file.path.stem.startswith("_"):
            return
        found = innermost(
            where=where,
            among=[
                (address, directory) for address, directory in layout.items() if directory.required
            ],
        )
        if found is None or (suffix := found[1].suffix) is None:
            return
        declared = list(declarations(tree=file.tree))
        if not declared:
            return
        yield from cls._violations(
            file=file,
            declared=declared,
            suffix=suffix,
        )

    @classmethod
    def _violations(
        cls,
        *,
        file: ParsedFile,
        declared: list[Declaration],
        suffix: str,
    ) -> Iterator[Violation]:
        required = [one for one in declared if one.name.endswith(suffix)]
        if not required:
            yield cls._says(
                file=file,
                node=declared[0],
                message=(
                    f"the module declares {cls._listed(declared=declared)}, "
                    f"but a module in this directory declares a ...{suffix} class"
                ),
            )
            return
        if len(required) > 1:
            yield cls._says(
                file=file,
                node=required[1],
                message=(
                    f"the module holds {cls._listed(declared=required)}; "
                    f"one ...{suffix} per module, and the module is named after it"
                ),
            )
            return
        ahead = cls._ahead(
            declared=declared,
            suffix=suffix,
        )
        if ahead is not None:
            yield cls._says(
                file=file,
                node=ahead,
                message=(
                    f"{ahead.name} is declared above the ...{suffix} the module "
                    f"exists for; helpers belong below it"
                ),
            )

    @staticmethod
    def _ahead(
        *,
        declared: list[Declaration],
        suffix: str,
    ) -> Declaration | None:
        """The first declaration that stands above the required class."""
        for one in declared:
            if one.name.endswith(suffix):
                return None
            if one.kind not in VOCABULARY:
                return one
        return None

    @staticmethod
    def _says(
        *,
        file: ParsedFile,
        node: Declaration,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=node.node,
            path=file.path,
            code=CODE,
            message=message,
        )

    @staticmethod
    def _listed(*, declared: list[Declaration]) -> str:
        return ", ".join(one.name for one in declared)
