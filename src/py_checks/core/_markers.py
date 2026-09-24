"""The mark that lifts a check from a line.

One shape for every rule: `# check-ok: <code>[, <code>]: <reason>`. A rule knows
nothing about marks — the core lifts violations, so both the syntax and the
demand for a reason are the same for every check.

The code is required: a mark lifts the named rule, not everything at once. The
reason is required for the same reason `# noqa` needs one in review: half a
year later nobody remembers whose library dictates the signature.

A group of rules has its own short word — `# signature-ok` for the whole
`signatures` package. It lifts any check in the group: people remember the
group ("this is about signatures"), not forty codes. The canonical
`# check-ok: <code>` lifts exactly one rule and always works.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from py_checks.core._violation import Violation

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator, Mapping, Sequence
    from pathlib import Path

    from py_checks.core._source import ParsedFile

MARKER: Final = "# check-ok:"

CODE: Final = "check-ok"

SHAPE: Final = "`# check-ok: <code>: <reason>`"

# A rule code looks like this and nothing else. The check is not there for
# strictness: the same word appears in the docs and in error messages, and such
# a line must not be read as a mark. Anything that does not look like a code is
# just text.
NAME: Final = re.compile(r"[a-z][a-z0-9_-]*")


@dataclass(frozen=True, slots=True)
class Marker:
    """What a mark says: which rules it lifts and why."""

    codes: frozenset[str]
    reason: str
    column: int


def markers(
    *,
    line: str,
    aliases: Mapping[str, frozenset[str]],
) -> tuple[Marker, ...]:
    """The marks on a line: there may be several.

    A signature laid out in a column gathers marks onto one line —
    `# signature-ok: the library calls it this way  # type-ok: raw input` —
    and both must lift.

    Parsing deliberately does not fail on a malformed mark: a mark with no
    code or no reason is read and ends up in `complaints`, otherwise nobody
    would hear about it.
    """
    found = sorted(
        _starts(
            line=line,
            aliases=aliases,
        )
    )
    bounds = [*(start for start, _ in found), len(line)]
    return tuple(
        marker
        for number, (start, word) in enumerate(found)
        if (
            marker := _marker(
                text=line[start : bounds[number + 1]],
                word=word,
                aliases=aliases,
                column=start + 1,
            )
        )
    )


def _starts(
    *,
    line: str,
    aliases: Mapping[str, frozenset[str]],
) -> Iterator[tuple[int, str]]:
    for word in (MARKER, *aliases):
        start = line.find(word)
        if start != -1:
            yield start, word


def _marker(
    *,
    text: str,
    word: str,
    aliases: Mapping[str, frozenset[str]],
    column: int,
) -> Marker | None:
    tail = text.removeprefix(word)
    if word != MARKER:
        return Marker(
            codes=aliases[word],
            reason=tail.removeprefix(":").strip(),
            column=column,
        )
    codes, _, reason = tail.partition(":")
    if not _named(text=codes):
        return None
    return Marker(
        codes=frozenset(_codes(text=codes)),
        reason=reason.strip(),
        column=column,
    )


def surviving(
    *,
    violations: Sequence[Violation],
    file: ParsedFile,
    aliases: Mapping[str, frozenset[str]],
) -> list[Violation]:
    """The violations no mark has lifted."""
    return [
        violation
        for violation in violations
        if not _covered(
            violation=violation,
            file=file,
            aliases=aliases,
        )
    ]


def complaints(
    *,
    file: ParsedFile,
    aliases: Mapping[str, frozenset[str]],
    known: Collection[str],
) -> Iterator[Violation]:
    """A mark that lifts nothing is a mark that silently does not work.

    A typo in a rule code looks like a disabled check, while in fact the check
    runs and simply does not see the mark. So such a mark is a violation
    itself.
    """
    for number, line in enumerate(file.lines, start=1):
        for marker in markers(
            line=line,
            aliases=aliases,
        ):
            yield from _wrong(
                marker=marker,
                path=file.path,
                line=number,
                known=known,
            )


def _named(*, text: str) -> bool:
    """Whether what is listed looks like rule codes.

    Empty space after the mark is a mark too, just without a code: `complaints`
    will report it. But `# check-ok: <code>` from the docs does not count as a
    mark, otherwise the library would catch its own text.
    """
    names = list(_codes(text=text))
    return not names or all(NAME.fullmatch(name) for name in names)


def _codes(*, text: str) -> Iterator[str]:
    for code in text.split(","):
        if stripped := code.strip():
            yield stripped


def _covered(
    *,
    violation: Violation,
    file: ParsedFile,
    aliases: Mapping[str, frozenset[str]],
) -> bool:
    return any(
        violation.code in marker.codes
        for line in _span(
            violation=violation,
            file=file,
        )
        for marker in markers(
            line=line,
            aliases=aliases,
        )
    )


def _span(
    *,
    violation: Violation,
    file: ParsedFile,
) -> tuple[str, ...]:
    """The lines searched for a mark.

    A violation points at the first line of what it found, while the mark
    belongs at the end: a signature laid out in a column carries it on its last
    line. So a check that spans several lines gives `end_line`, and the mark is
    searched for in all of them.
    """
    last = max(violation.end_line or violation.line, violation.line)
    return file.lines[violation.line - 1 : last]


def _wrong(
    *,
    marker: Marker,
    path: Path,
    line: int,
    known: Collection[str],
) -> Iterator[Violation]:
    if not marker.codes:
        yield _complaint(
            path=path,
            line=line,
            column=marker.column,
            message=f"the mark needs a check code: {SHAPE}",
        )
    for code in sorted(marker.codes.difference(known)):
        yield _complaint(
            path=path,
            line=line,
            column=marker.column,
            message=f"there is no check `{code}`, the mark lifts nothing",
        )
    if not marker.reason:
        yield _complaint(
            path=path,
            line=line,
            column=marker.column,
            message=f"the mark needs a reason: {SHAPE}",
        )


def _complaint(
    *,
    path: Path,
    line: int,
    column: int,
    message: str,
) -> Violation:
    return Violation(
        path=path,
        line=line,
        column=column,
        code=CODE,
        message=message,
    )
