"""The length of a module."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from pydantic import Field

from py_checks.checks.signatures._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "module-length"


class ModuleLengthSettings(CheckSettings):
    max_lines: int = Field(
        default=600,
        gt=0,
    )


class ModuleLength:
    """Fails when a module is longer than the limit.

    A long module is usually several modules that did not split up in time.
    Every line of the file is counted, blank ones and comments included: the
    rule is about the size of a file the reader has to hold in their head, not
    about how dense the code in it is.

    Settings: `max-lines`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ModuleLengthSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    def run(
        self,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=ModuleLengthSettings,
            code=CODE,
        )
        length = len(file.lines)
        if length <= limits.max_lines:
            return
        yield Violation(
            path=file.path,
            line=limits.max_lines + 1,
            column=1,
            code=CODE,
            message=f"{length} lines, the limit is {limits.max_lines}",
        )
