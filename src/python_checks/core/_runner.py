"""Прогон проверок по файлам."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Final

from python_checks.core import _registry
from python_checks.core._errors import ParseError
from python_checks.core._markers import complaints, surviving
from python_checks.core._source import ParsedFile
from python_checks.core._violation import Violation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from pathlib import Path

    from python_checks.config import CheckSettings, Config
    from python_checks.core._protocols import FileCheck

SYNTAX: Final = "syntax"


def inspect(
    *,
    files: Sequence[Path],
    checks: Sequence[FileCheck],
    config: Config,
    root: Path | None = None,
) -> list[Violation]:
    """Все нарушения по всем файлам.

    Внешний цикл по файлам, а не по проверкам: файл читается и разбирается один
    раз, а проверок на него много.
    """
    settings = {
        check.code: config.settings_for(
            code=check.code,
            model=check.Settings,
        )
        for check in checks
    }
    registered = _registry.available()
    aliases = _aliases(registered=registered)
    source = root / config.src if root is not None else None
    violations: list[Violation] = []
    for path in files:
        violations.extend(
            _inspect_file(
                path=path,
                checks=checks,
                settings=settings,
                source=source,
                aliases=aliases,
                known=frozenset(registered),
            )
        )
    return violations


def _aliases(*, registered: Mapping[str, FileCheck]) -> dict[str, frozenset[str]]:
    """Слово группы и все правила, которые оно снимает.

    Слово у группы одно на всех, поэтому `# signature-ok` снимает любую
    проверку из `signatures`: человек помнит группу, а не сорок кодов. Когда
    нужно снять ровно одно правило, для этого есть `# check-ok: <код>`.
    """
    groups: dict[str, set[str]] = defaultdict(set)
    for code, check in registered.items():
        groups[check.marker].add(code)
    return {marker: frozenset(codes) for marker, codes in groups.items()}


def _inspect_file(
    *,
    path: Path,
    checks: Sequence[FileCheck],
    settings: Mapping[str, CheckSettings],
    source: Path | None,
    aliases: Mapping[str, frozenset[str]],
    known: Collection[str],
) -> list[Violation]:
    file = ParsedFile.from_path(
        path=path,
        source=source,
    )
    found: list[Violation] = []
    for check in checks:
        try:
            found.extend(
                check.run(
                    file=file,
                    settings=settings[check.code],
                )
            )
        except ParseError as error:
            return [_broken(error=error)]
    kept = surviving(
        violations=found,
        file=file,
        aliases=aliases,
    )
    return [
        *kept,
        *complaints(
            file=file,
            aliases=aliases,
            known=known,
        ),
    ]


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
