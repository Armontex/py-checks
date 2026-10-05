"""The fingerprint on a translation's first line."""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING

from py_checks.translations._constants import STAMP, STAMPED
from py_checks.translations._errors import TranslationError
from py_checks.translations._tree import source_of

if TYPE_CHECKING:
    from pathlib import Path


def fingerprint(*, path: Path) -> str:
    """The SHA-256 of the file's raw bytes.

    No normalisation: the end-of-file and whitespace hooks keep the bytes
    stable, and a whitespace-only edit that asks for a re-stamp is a cheap
    false alarm.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stamped(*, path: Path) -> str | None:
    """The digest on the first line; `None` if the first line is not a fingerprint."""
    first = path.read_text(encoding="utf-8").partition("\n")[0]
    found = STAMPED.match(first)
    return None if found is None else found.group("digest")


def stamp(
    *,
    root: Path,
    translation: str,
) -> None:
    """Write or refresh the fingerprint of one translation.

    It never creates a translation: the translator writes it, then stamps it.
    And it is never part of `run --fix`: a fix that rewrote the hash would
    bless a translation nobody updated, the one thing the check exists to stop.
    """
    pair = source_of(translation=translation)
    if pair is None:
        message = f"{translation} is not a translation: it lies outside docs/langs/<lang>/"
        raise TranslationError(message)
    path = root / translation
    source = root / pair[1]
    if not path.is_file():
        message = f"{translation} does not exist: write the translation, then stamp it"
        raise TranslationError(message)
    if not source.is_file():
        message = f"{translation} translates nothing: {pair[1]} does not exist"
        raise TranslationError(message)
    text = path.read_text(encoding="utf-8")
    body = text.partition("\n")[2] if stamped(path=path) is not None else text
    line = STAMP.format(digest=fingerprint(path=source))
    path.write_text(f"{line}\n{body}", encoding="utf-8")
