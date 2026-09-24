"""A directory declares what lives in it."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._kind import declarations
from py_checks.checks._layout import SECTION, Layout, innermost
from py_checks.checks._location import place
from py_checks.checks.placement._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "class-modules"


class ClassModules:
    """Fails when a module holds what its directory does not allow.

    A directory names what lives in it, and nothing else sits beside that. A
    helper that drifted into a use case module is either part of the class,
    and then it is a static method inside it, or shared, and then it belongs
    where the rest of the shared code lives. An enum that wandered into `dto/`
    is the same story.

    Imports, constants, `if TYPE_CHECKING` blocks and the docstring are allowed
    everywhere: the rule is about what a module declares, not what it uses.

    The address in a block's heading is a path, not a directory name, and that
    matters: `application/services` holds an orchestrating class, while
    `domain/services` holds functions, rules that compare two facts. One word,
    two different animals. A directory the layout says nothing about is not
    the rule's business.

    Settings: `only` in the shared `[layout]` table.
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
        if where is None:
            return
        found = innermost(
            where=where,
            among=[(address, directory) for address, directory in layout.items() if directory.only],
        )
        if found is None:
            return
        address, directory = found
        for declared in declarations(tree=file.tree):
            # No kind to see, nothing to judge: a class with a base from another module.
            if declared.kind is None or declared.kind in directory.only:
                continue
            yield Violation.from_node(
                node=declared.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{declared.name}: {declared.kind.said}; {address} holds only "
                    f"{', '.join(sorted(one.said for one in directory.only))}"
                ),
            )
