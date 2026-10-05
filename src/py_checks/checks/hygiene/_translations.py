"""A translated document still says what its English source says."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks.hygiene._marker import MARKER
from py_checks.core import Scope, Violation, settings_as
from py_checks.translations import (
    SECTION,
    TranslationError,
    TranslationsSettings,
    fingerprint,
    selected,
    source_of,
    stamped,
    tracked,
    translation_of,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from py_checks.config import CheckSettings

CODE: Final = SECTION

FIRST: Final = 1


class Translations:
    """Fails when a translation is missing or no longer matches its source.

    A translation goes stale the moment the English changes, and nothing
    tells anyone: its reader reads a document that is no longer true. A
    document nobody translated is the same problem one step earlier. So the
    check refuses both, the way `py-checks sync --check` refuses a generated
    file that no longer matches what it is built from.

    English is the source, and each language mirrors the repository under
    `docs/langs/<lang>/` by the same path: `docs/testing.md` is translated in
    `docs/langs/ru/docs/testing.md`. The first line of a translation is the
    SHA-256 of the source as it was when translated, written by
    `py-checks translations stamp <translation>` — never by `run --fix`, which
    would bless a translation nobody updated.

    Refused: a selected file with no translation; a translation whose source
    changed since; a translation whose source is gone or no longer selected;
    a first line that is not a fingerprint.

    Candidates are the files git knows and does not ignore, so `.venv/` never
    needs excluding, and `docs/langs/` is never asked for its own translation.

    Settings: `langs`, `files`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = TranslationsSettings
    scope: ClassVar[Scope] = Scope.PROJECT
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        root: Path,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=TranslationsSettings,
            code=CODE,
        )
        if not limits.langs or not limits.files:
            return
        try:
            paths = tracked(root=root)
        except TranslationError as error:
            yield cls._says(
                path=root,
                message=str(error),
            )
            return
        sources = selected(
            paths=paths,
            files=limits.files,
        )
        for lang in limits.langs:
            yield from cls._missing_or_stale(
                root=root,
                sources=sources,
                lang=lang,
            )
            yield from cls._orphans(
                root=root,
                paths=paths,
                sources=frozenset(sources),
                lang=lang,
            )

    @classmethod
    def _missing_or_stale(
        cls,
        *,
        root: Path,
        sources: list[str],
        lang: str,
    ) -> Iterator[Violation]:
        """Every selected source: translated, and translated from what it says now."""
        for source in sources:
            translation = translation_of(
                source=source,
                lang=lang,
            )
            path = root / translation
            if not path.is_file():
                yield cls._says(
                    path=root / source,
                    message=f"{source} has no {lang} translation: {translation}",
                )
                continue
            digest = stamped(path=path)
            if digest is None:
                yield cls._says(
                    path=path,
                    message=(
                        f"{translation}: the first line is not a fingerprint; after translating, "
                        f"run `py-checks translations stamp {translation}`"
                    ),
                )
            elif digest != fingerprint(path=root / source):
                yield cls._says(
                    path=path,
                    message=f"{source} changed since {translation} was translated",
                )

    @classmethod
    def _orphans(
        cls,
        *,
        root: Path,
        paths: list[str],
        sources: frozenset[str],
        lang: str,
    ) -> Iterator[Violation]:
        """A translation whose source is gone or no longer selected."""
        for path in paths:
            pair = source_of(translation=path)
            if pair is None or pair[0] != lang or pair[1] in sources:
                continue
            yield cls._says(
                path=root / path,
                message=f"{path} translates nothing",
            )

    @staticmethod
    def _says(
        *,
        path: Path,
        message: str,
    ) -> Violation:
        return Violation(
            path=path,
            line=FIRST,
            column=FIRST,
            code=CODE,
            message=message,
        )
