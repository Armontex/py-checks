"""Running the checks over the files."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING, Final

from py_checks.core import _registry
from py_checks.core._errors import ParseError
from py_checks.core._markers import complaints, surviving
from py_checks.core._protocols import section_of
from py_checks.core._source import ParsedFile
from py_checks.core._violation import Violation

if TYPE_CHECKING:
    from collections.abc import Collection, Mapping, Sequence
    from pathlib import Path

    from py_checks.config import CheckSettings, Config
    from py_checks.core._protocols import Check, FileCheck, ProjectCheck
    from py_checks.core._registry import Checks

SYNTAX: Final = "syntax"


def survey(
    *,
    chosen: Checks,
    files: Sequence[Path],
    config: Config,
    root: Path,
) -> list[Violation]:
    """Every violation of the chosen rules: file rules by file, project rules by root.

    The split is made once, here, because a rule's kind shows only in what it
    is given: a rule judging a file and a rule judging the project have
    different `run`s, and putting them in one loop would be a pretence.
    """
    return [
        *inspect(
            files=files,
            checks=list(chosen.files.values()),
            config=config,
            root=root,
        ),
        *examine(
            checks=list(chosen.project.values()),
            config=config,
            root=root,
        ),
    ]


def inspect(
    *,
    files: Sequence[Path],
    checks: Sequence[FileCheck],
    config: Config,
    root: Path | None = None,
) -> list[Violation]:
    """Every violation across every file.

    The outer loop is over files, not checks: a file is read and parsed once,
    and there are many checks for it.
    """
    settings = {
        check.code: config.settings_for(
            code=section_of(check=check),
            model=check.Settings,
        )
        for check in checks
    }
    registered = _registry.available().listed
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


def examine(
    *,
    checks: Sequence[ProjectCheck],
    config: Config,
    root: Path,
) -> list[Violation]:
    """The violations of the rules that need the whole project.

    Each is called once: what to read — the manifest, a pair of files, the
    tree — it decides itself.
    """
    return [
        violation
        for check in checks
        for violation in check.run(
            root=root,
            settings=config.settings_for(
                code=section_of(check=check),
                model=check.Settings,
            ),
        )
    ]


def _aliases(*, registered: Mapping[str, Check]) -> dict[str, frozenset[str]]:
    """A group's word and every rule it lifts.

    A group has one word for all of its rules, so `# signature-ok` lifts any
    check from `signatures`: people remember the group, not forty codes. When
    exactly one rule has to be lifted, there is `# check-ok: <code>`.
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
    """A broken file is one violation, not a crash of the whole run.

    Otherwise one file with half-written syntax hides the violations in all
    the others.
    """
    return Violation(
        path=error.path,
        line=error.error.lineno or 1,
        column=error.error.offset or 1,
        code=SYNTAX,
        message=error.error.msg,
    )
