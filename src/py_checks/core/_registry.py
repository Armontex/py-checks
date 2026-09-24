"""Which checks exist and how they are found."""

from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

from py_checks.core._constants import GROUP
from py_checks.core._errors import UnknownCheckError
from py_checks.core._protocols import Scope

if TYPE_CHECKING:
    from collections.abc import Collection

    from py_checks.core._protocols import Check, FileCheck, ProjectCheck


@dataclass(frozen=True, slots=True)
class Checks:
    """The rules, sorted by what they are given: a file or the project root.

    One and the same shape describes both everything installed and what was
    picked for this run — so the choice does not turn into a branch for
    everyone who receives it: the run, the list and the explanation all speak
    of the same set.
    """

    files: dict[str, FileCheck]
    project: dict[str, ProjectCheck]

    @property
    def listed(self) -> dict[str, Check]:
        """Every rule by code, whatever its kind."""
        return {**self.files, **self.project}

    def only(self, *, codes: Collection[str]) -> Checks:
        """The same set, narrowed to the named codes."""
        return Checks(
            files={code: check for code, check in self.files.items() if code in codes},
            project={code: check for code, check in self.project.items() if code in codes},
        )


@cache
def available() -> Checks:
    """Every check declared through entry points.

    This is how a project or a team adds a rule of its own: it installs its
    own package alongside, with a record in this same group, and the library
    needs no fork. The kind of rule — whether it is given a file or the
    project root — the rule declares itself.

    Read once: loading means importing every declared module, and the
    registry is asked by the run, the selection and the explanation alike.
    """
    files: dict[str, FileCheck] = {}
    project: dict[str, ProjectCheck] = {}
    for entry in sorted(entry_points(group=GROUP), key=lambda entry: entry.name):
        check = entry.load()()
        if check.scope is Scope.FILE:
            files[check.code] = check
        else:
            project[check.code] = check
    return Checks(
        files=files,
        project=project,
    )


def get(*, code: str) -> Check:
    checks = available().listed
    if code not in checks:
        raise UnknownCheckError(
            code=code,
            known=tuple(sorted(checks)),
        )
    return checks[code]
