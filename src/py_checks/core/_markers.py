"""Маркер, которым строка снимается с проверки.

Форма одна на все правила: `# check-ok: <код>[, <код>]: <причина>`. Правило про
маркеры не знает ничего — нарушения снимает ядро, поэтому и синтаксис, и
требование причины у всех проверок одинаковые.

Код обязателен: маркер снимает названное правило, а не всё подряд. Причина
обязательна по той же причине, по которой её требует `# noqa` в ревью: через
полгода никто не помнит, чья это библиотека диктует подпись.

У группы правил есть своё короткое слово — `# signature-ok` на весь пакет
`signatures`. Оно снимает любую проверку группы: человек помнит группу («это
про подписи»), а не сорок кодов. Канонический `# check-ok: <код>` снимает ровно
одно правило и работает всегда.
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

SHAPE: Final = "`# check-ok: <код>: <причина>`"

# Код правила выглядит так и не иначе. Проверка нужна не ради строгости: это
# же слово стоит в документации и в сообщениях об ошибках, и такая строка не
# должна читаться как пометка. Всё, что на код не похоже, — просто текст.
NAME: Final = re.compile(r"[a-z][a-z0-9_-]*")


@dataclass(frozen=True, slots=True)
class Marker:
    """Что написано в маркере: какие правила он снимает и почему."""

    codes: frozenset[str]
    reason: str
    column: int


def markers(
    *,
    line: str,
    aliases: Mapping[str, frozenset[str]],
) -> tuple[Marker, ...]:
    """Маркеры строки: их может быть несколько.

    Подпись в столбик собирает пометки в одну строку — `# signature-ok: так
    зовёт библиотека  # type-ok: сырой ввод`, — и снимать они должны обе.

    Разбор нарочно не падает на кривой записи: маркер без кода или без причины
    читается и попадает в `complaints`, иначе о нём никто бы не узнал.
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
    """Нарушения, которые никто не снял маркером."""
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
    """Маркер, который ничего не снимает, — молча неработающий маркер.

    Опечатка в коде правила выглядит как отключённая проверка, а на деле
    проверка работает и просто не видит пометки. Поэтому такой маркер — сам
    нарушение.
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
    """Похоже ли перечисленное на коды правил.

    Пустое место после маркера — тоже пометка, только без кода: о ней скажет
    `complaints`. А вот `# check-ok: <код>` из документации пометкой не
    считается, иначе библиотека ловила бы собственный текст.
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
    """Строки, в которых ищем маркер.

    Нарушение указывает на первую строку того, что нашло, а пометке место в
    конце: подпись в столбик несёт её на последней строке. Поэтому проверка,
    занимающая несколько строк, говорит `end_line`, и маркер ищется во всех.
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
            message=f"маркеру нужен код проверки: {SHAPE}",
        )
    for code in sorted(marker.codes.difference(known)):
        yield _complaint(
            path=path,
            line=line,
            column=marker.column,
            message=f"нет проверки `{code}`, маркер ничего не снимает",
        )
    if not marker.reason:
        yield _complaint(
            path=path,
            line=line,
            column=marker.column,
            message=f"маркеру нужна причина: {SHAPE}",
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
