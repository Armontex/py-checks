"""An edit to the source and how it is applied."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import accumulate
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class Edit:
    """A replacement of a piece of source; lines and columns as in a violation, from 1.

    An insertion is a replacement of empty space: the start and the end are
    the same. An edit describes only the piece it changes, so everything else
    in the file — comments, line breaks, someone else's formatting — stays
    untouched.
    """

    line: int
    column: int
    end_line: int
    end_column: int
    text: str


def column(
    *,
    line: str,
    offset: int,
) -> int:
    """The edit's column from the tree's offset, from 1.

    `ast` counts `col_offset` in utf-8 BYTES, while an edit indexes the line
    by characters. The two agree only up to the first non-ascii character on
    the line: one Russian word in a literal earlier on the line, and the comma
    lands in the wrong place.
    """
    return len(line.encode("utf-8")[:offset].decode("utf-8", errors="ignore")) + 1


def apply(
    *,
    text: str,
    edits: Sequence[Edit],
) -> str:
    """The source with every edit applied.

    Edits are applied from the end of the file to the start: that way the
    positions of the edits not yet applied stay correct and need no
    recalculation. An edit that overlaps one already applied is skipped — two
    checks arguing over one piece of text must settle it in separate runs, not
    overwrite each other.
    """
    starts = _starts(text=text)
    applied = len(text)
    result = text
    for edit in sorted(
        edits,
        key=lambda edit: (edit.line, edit.column),
        reverse=True,
    ):
        start = _offset(
            starts=starts,
            line=edit.line,
            column=edit.column,
        )
        end = _offset(
            starts=starts,
            line=edit.end_line,
            column=edit.end_column,
        )
        if end > applied:
            continue
        result = result[:start] + edit.text + result[end:]
        applied = start
    return result


def _starts(*, text: str) -> tuple[int, ...]:
    """The offset of each line's start from the start of the file."""
    lengths = (len(line) for line in text.splitlines(keepends=True))
    return (0, *accumulate(lengths))


def _offset(
    *,
    starts: Sequence[int],
    line: int,
    column: int,
) -> int:
    return starts[min(line, len(starts)) - 1] + column - 1
