"""Where a file lies inside its package.

A rule about imports speaks of a place: "sqlalchemy lives in `infra/database`".
The place is counted from the source root, which the core knows from the
settings. It cannot be guessed from `__init__.py`: a directory without one
turns up in the middle of a package too — in one of the services half the
repositories lie that way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from py_checks.config import CheckSettings
from py_checks.core import ANY, depth

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from py_checks.core import ParsedFile

INIT: Final = "__init__"

SEPARATOR: Final = "/"

# A package and at least one step inside it: a file lying right in the source
# root is in no package, and there is nothing to say about its place.
INSIDE: Final = 2


@dataclass(frozen=True, slots=True)
class Place:
    """A file's root package, its address inside it and the directories it lies in.

    The directories are kept apart from the address because a zone is a
    directory: `domain` means `domain/` and what is under it, not a module
    that happens to be called `domain.py` in `application/exceptions/`. The
    file's own name answers only to `*`: `domain/*` still takes
    `domain/exceptions.py`, since `*` is any piece and a module is one.
    """

    package: str
    parts: tuple[str, ...]
    directories: tuple[str, ...]

    @property
    def where(self) -> str:
        return "/".join(self.parts)

    def under(self, *, prefix: str) -> bool:
        """Whether the file lies under this path; an empty path allows nothing."""
        if not prefix:
            return False
        wanted = tuple(prefix.split(SEPARATOR))
        return self.parts[: len(wanted)] == wanted

    def inside(self, *, zones: Iterable[str]) -> bool:
        """Whether the file lies in at least one of these zones.

        Only directories count; the file's own name matches `*` and nothing
        else. Zones add up rather than argue: a rule works where it was asked
        to, and is silent everywhere else.
        """
        return any(
            depth(
                parts=self.parts if zone.split(SEPARATOR)[-1] == ANY else self.directories,
                path=zone,
            )
            is not None
            for zone in zones
        )

    def anywhere(self, *, zones: Iterable[str]) -> bool:
        """Whether the file is at one of these addresses, a directory or a module."""
        return any(self.holds(path=zone) for zone in zones)

    def holds(self, *, path: str) -> bool:
        """Whether these address parts run in a row anywhere inside it.

        The address includes the module's name, so `exceptions` matches both as
        a directory and as the file `exceptions.py`: to the refusal vocabulary
        it is one and the same place.
        """
        return (
            depth(
                parts=self.parts,
                path=path,
            )
            is not None
        )

    def within(self, *, directory: str) -> int | None:
        """Where the deepest occurrence of these directories ends, or `None`.

        The file's name does not count: this is about a directory, not a
        module. The end rather than the start, because the nesting of two keys
        of different length can only be compared by where they end — the one
        that ends later is deeper.
        """
        return depth(
            parts=self.parts[:-1],
            path=directory,
        )


class ZonedSettings(CheckSettings):
    """The settings of a rule that does not work everywhere.

    `zones` are the places where the rule judges; an empty list means the rule
    is silent. Silent, not judging everywhere: a convention about repositories
    is wrong for use cases, and a rule whose zone was forgotten had better say
    nothing than say something untrue across the whole tree.
    """

    zones: tuple[str, ...] = ()


def zoned(
    *,
    file: ParsedFile,
    zones: Iterable[str],
) -> Place | None:
    """The file's address if it is in one of the zones; otherwise `None`: nothing to say."""
    where = place(file=file)
    if where is None or not where.inside(zones=zones):
        return None
    return where


def place(*, file: ParsedFile) -> Place | None:
    """The file's address; `None` if the source root is unknown or the file is outside it."""
    if file.source is None:
        return None
    relative = _relative(
        path=file.path,
        source=file.source,
    )
    if relative is None or len(relative) < INSIDE:
        return None
    parts = relative[1:]
    if parts[-1] == INIT:
        parts = parts[:-1]
    return Place(
        package=relative[0],
        parts=parts,
        directories=relative[1:-1],
    )


def _relative(
    *,
    path: Path,
    source: Path,
) -> tuple[str, ...] | None:
    try:
        inside = path.resolve().relative_to(source.resolve())
    except ValueError:
        return None
    return inside.with_suffix("").parts
