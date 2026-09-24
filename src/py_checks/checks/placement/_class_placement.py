"""A class lives where classes of its kind live."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._kind import declarations
from py_checks.checks._layout import SECTION, Layout, claimants
from py_checks.checks._location import place
from py_checks.checks.placement._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "class-placement"


class ClassPlacement:
    """Fails when a class lies somewhere other than where its kind lives.

    The directory names the kind, and the reader finds the port without
    opening a file. A home is declared in the layout: `home` is about the kind
    of declaration, `suffix` about the name. One kind may have several
    addresses, and then any of them is home: a repository port and its
    implementation lawfully live in two places, and the refusal vocabulary in
    both `errors/` and `exceptions.py`.

    A kind the layout says nothing about is not the rule's business: until
    `dataclass` has named its home, it lives anywhere. Once it has, every home
    is on the list, the domain included: a value object is a dataclass too.

    `area` narrows the claim to part of the tree: the `dto` convention is
    written for the application layer, while a dataclass in the bootstrap or
    in observability is a way to put three fields side by side, not a subject.

    Settings: `home`, `suffix` and `area` in the shared `[layout]` table.
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
        for declared in declarations(tree=file.tree):
            homes = claimants(
                declared=declared,
                layout=layout,
                where=where,
            )
            if not homes or any(where.holds(path=home.address) for home in homes):
                continue
            yield Violation.from_node(
                node=declared.node,
                path=file.path,
                code=CODE,
                message=(
                    f"{declared.name} {homes[0].said}; "
                    f"it belongs in {', '.join(home.address for home in homes)}"
                ),
            )
