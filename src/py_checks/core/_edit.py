"""Правка исходника и то, как она накладывается."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import accumulate
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence


@dataclass(frozen=True, slots=True)
class Edit:
    """Замена куска исходника, строки и колонки — как у нарушения, с единицы.

    Вставка — это замена пустого места: начало и конец совпадают. Правка
    описывает только тот кусок, который меняет, поэтому всё остальное в файле —
    комментарии, переносы, чужое форматирование — остаётся нетронутым.
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
    """Колонка правки по смещению из дерева, с единицы.

    `ast` считает `col_offset` в БАЙТАХ utf-8, а правка индексирует строку
    символами. Совпадает это ровно до первого не-ascii символа в строке: одно
    русское слово в литерале раньше по строке — и запятая встаёт не туда.
    """
    return len(line.encode("utf-8")[:offset].decode("utf-8", errors="ignore")) + 1


def apply(
    *,
    text: str,
    edits: Sequence[Edit],
) -> str:
    """Исходник со всеми правками.

    Накладываются с конца файла к началу: тогда позиции ещё не наложенных
    правок остаются верными и пересчитывать их не нужно. Правки, залезающие на
    уже наложенную, пропускаются — две проверки, спорящие за один кусок текста,
    должны разойтись в разных прогонах, а не перезаписывать друг друга.
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
    """Смещение начала каждой строки от начала файла."""
    lengths = (len(line) for line in text.splitlines(keepends=True))
    return (0, *accumulate(lengths))


def _offset(
    *,
    starts: Sequence[int],
    line: int,
    column: int,
) -> int:
    return starts[min(line, len(starts)) - 1] + column - 1
