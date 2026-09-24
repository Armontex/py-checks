"""How the library sees a rule."""

from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from py_checks.config import CheckSettings
    from py_checks.core._source import ParsedFile
    from py_checks.core._violation import Violation


class Scope(StrEnum):
    """What a rule is given to judge.

    The rule declares its kind itself, not the entry point group: that way the
    author of a third-party package writes one record, and `list` and `explain`
    see every rule at once without merging two registries into one.
    """

    # One file, parsed by the core: most rules are of this kind.
    FILE = "file"

    # The project root: the manifest, two files of the repository agreeing with each other.
    PROJECT = "project"

    # The same as `PROJECT`, but the rule needs a live environment — a database,
    # the network, a long run. Such a rule is not part of a normal run: it is
    # called by name or in CI, otherwise the commit hook starts waiting for a
    # database.
    ENVIRONMENT = "environment"


@runtime_checkable
class FileCheck(Protocol):
    """A rule for which one file is enough.

    Everything else — finding files, parsing, settings, output — the core
    does. A check knows only its own condition and returns violations without
    printing anything: otherwise the output format would spread across forty
    rules.
    """

    code: ClassVar[str]
    Settings: ClassVar[type[CheckSettings]]
    scope: ClassVar[Scope]

    # The word of the group the rule belongs to: `# signature-ok` lifts any
    # check from `signatures`. It is written once per package, because people
    # remember the group ("this is about signatures"), not forty codes. The
    # canonical `# check-ok: <code>` always works and lifts exactly one rule.
    marker: ClassVar[str]

    def run(
        self,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]: ...


@runtime_checkable
class ProjectCheck(Protocol):
    """A rule for which one file is not enough.

    The dependency manifest, two files of the repository agreeing with each
    other — what lives not in the source but in the project. Such a rule is
    called once per run and decides itself what to read; the core gives it the
    root and the settings.
    """

    code: ClassVar[str]
    Settings: ClassVar[type[CheckSettings]]
    scope: ClassVar[Scope]
    marker: ClassVar[str]

    def run(
        self,
        *,
        root: Path,
        settings: CheckSettings,
    ) -> Iterator[Violation]: ...


# A rule is one of two things: it judges a file or it judges the project.
# Where all that matters is that it has a code and a description (the list,
# the explanation), either will do.
type Check = FileCheck | ProjectCheck


def section_of(*, check: Check) -> str:
    """A rule's settings section: its code, unless the rule says otherwise.

    The layout rules say otherwise: four of them read one `[layout]` table,
    because they describe the same directory from four sides, and four tables
    about one thing would drift apart. They know nothing about each other —
    only which section to read from.
    """
    return getattr(check, "section", check.code)
