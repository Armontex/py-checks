"""Applying edits to files."""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from py_checks.core._edit import apply
from py_checks.core._registry import available

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from py_checks.core._edit import Edit
    from py_checks.core._violation import Violation


@dataclass(frozen=True, slots=True)
class Patch:
    """An edit and the file it goes into: a repair may reach past the violation's own file."""

    path: Path
    edit: Edit


@dataclass(frozen=True, slots=True)
class Repair:
    """What a rule's own repair decided: the patches per violation, and what it left.

    Every patch of a violation is applied or none is: a signature changed
    without its callers is worse than a signature left alone. A violation
    whose fix depends on another's lists that one's patches as well, and the
    two stand or fall together.
    """

    patches: dict[Violation, tuple[Patch, ...]]
    left: list[Violation]


@runtime_checkable
class Repairing(Protocol):
    """A rule whose fix does not fit in the violation's own file.

    `keyword-only-arguments` makes a parameter named, and every positional
    caller across the project has to say the name too. Such a rule is asked
    only when `--fix` runs: finding the callers is a walk over the whole
    project, and a plain run has no use for it.
    """

    def repair(
        self,
        *,
        violations: Sequence[Violation],
        root: Path,
        source: Path,
    ) -> Repair: ...


def fix(
    *,
    violations: Sequence[Violation],
    root: Path,
    source: Path,
) -> tuple[list[Path], list[Violation]]:
    """Fix what can be fixed; return the changed files and what is left.

    A violation without an edit is not a failure of the autofix but an honest
    answer: `*args` cannot be fixed, the argument names are the author's to
    choose. Such violations are returned and go into the report as usual.

    A file the edits leave unparsable is not written: a fix that breaks the
    syntax breaks the next hook too, and that hook names the file, not the
    rule. Its violations go into the report as if there were no edits.
    """
    grouped: dict[str, list[Violation]] = defaultdict(list)
    for violation in violations:
        grouped[violation.code].append(violation)
    checks = available().listed
    patches: dict[Violation, tuple[Patch, ...]] = {}
    left: list[Violation] = []
    for code, found in grouped.items():
        check = checks.get(code)
        if isinstance(check, Repairing):
            repaired = check.repair(
                violations=found,
                root=root,
                source=source,
            )
            patches.update(repaired.patches)
            left.extend(repaired.left)
            continue
        for violation in found:
            if violation.edit is None:
                left.append(violation)
            else:
                patches[violation] = (
                    Patch(
                        path=violation.path,
                        edit=violation.edit,
                    ),
                )
    changed, failed = _write(patches=patches)
    return changed, [*left, *failed]


def _write(*, patches: dict[Violation, tuple[Patch, ...]]) -> tuple[list[Path], list[Violation]]:
    """Apply the patches, dropping every violation whose patches break a file.

    A dropped violation takes all its patches with it, so the files are worked
    out again without them until none breaks; only then is anything written.
    """
    failed: list[Violation] = []
    while True:
        texts, broken = _rewritten(patches=patches)
        if not broken:
            break
        failed.extend(broken)
        patches = {violation: own for violation, own in patches.items() if violation not in broken}
    for path, text in texts.items():
        path.write_text(text, encoding="utf-8")
    return sorted(texts), failed


def _rewritten(
    *,
    patches: dict[Violation, tuple[Patch, ...]],
) -> tuple[dict[Path, str], set[Violation]]:
    """The new text of every changed file, and the violations that broke one."""
    owners: dict[Path, dict[Edit, set[Violation]]] = defaultdict(lambda: defaultdict(set))
    for violation, own in patches.items():
        for patch in own:
            owners[patch.path][patch.edit].add(violation)
    texts: dict[Path, str] = {}
    broken: set[Violation] = set()
    for path, edits in owners.items():
        clashing = _overlapping(edits=edits)
        if clashing:
            broken.update(*(edits[edit] for edit in clashing))
            continue
        text = path.read_text(encoding="utf-8")
        fixed = apply(
            text=text,
            edits=list(edits),
        )
        try:
            ast.parse(fixed, filename=str(path))
        except SyntaxError:
            broken.update(*edits.values())
            continue
        if fixed != text:
            texts[path] = fixed
    return texts, broken


def _overlapping(*, edits: Iterable[Edit]) -> list[Edit]:
    """The edits that reach into each other's text.

    `apply` would skip one of them, and a fix half applied is the broken one:
    the signature changed and one caller did not.
    """
    ordered = sorted(
        edits,
        key=lambda edit: (edit.line, edit.column, edit.end_line, edit.end_column),
    )
    clashing: list[Edit] = []
    for before, after in zip(ordered, ordered[1:], strict=False):
        if (after.line, after.column) < (before.end_line, before.end_column):
            clashing.extend((before, after))
    return clashing
