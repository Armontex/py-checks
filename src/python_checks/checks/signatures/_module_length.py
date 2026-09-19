"""Длина модуля."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from pydantic import Field

from python_checks.checks.signatures._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "module-length"


class ModuleLengthSettings(CheckSettings):
    max_lines: int = Field(
        default=600,
        gt=0,
    )


class ModuleLength:
    """Падает, если модуль длиннее лимита.

    Длинный модуль — это обычно несколько модулей, которые не разъехались
    вовремя. Считаются все строки файла, включая пустые и комментарии: правило
    про размер файла, который приходится держать в голове, а не про плотность
    кода в нём.

    Настройка: `max-lines`.
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
            message=f"{length} строк, предел {limits.max_lines}",
        )
