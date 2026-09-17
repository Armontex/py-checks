"""Прогон проверок по файлам."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from python_checks.core._errors import ParseError
from python_checks.core._source import ParsedFile
from python_checks.core._violation import Violation

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from pathlib import Path

    from python_checks.config import CheckSettings, Config
    from python_checks.core._protocols import FileCheck

SYNTAX: Final = "syntax"


def inspect(
    *,
    files: Sequence[Path],
    checks: Sequence[FileCheck],
    config: Config,
) -> list[Violation]:
    """Все нарушения по всем файлам.

    Внешний цикл по файлам, а не по проверкам: файл читается и разбирается один
    раз, а проверок на него много.
    """
    settings = {
        check.code: config.settings_for(code=check.code, model=check.Settings) for check in checks
    }
    violations: list[Violation] = []
    for path in files:
        violations.extend(_inspect_file(path=path, checks=checks, settings=settings))
    return violations


def _inspect_file(
    *,
    path: Path,
    checks: Sequence[FileCheck],
    settings: Mapping[str, CheckSettings],
) -> list[Violation]:
    file = ParsedFile.from_path(path=path)
    found: list[Violation] = []
    for check in checks:
        try:
            found.extend(check.run(file=file, settings=settings[check.code]))
        except ParseError as error:
            return [_broken(error=error)]
    return found


def _broken(*, error: ParseError) -> Violation:
    """Сломанный файл — это одно нарушение, а не падение всего прогона.

    Иначе один файл с недописанным синтаксисом прячет нарушения во всех
    остальных.
    """
    return Violation(
        path=error.path,
        line=error.error.lineno or 1,
        column=error.error.offset or 1,
        code=SYNTAX,
        message=error.error.msg,
    )
