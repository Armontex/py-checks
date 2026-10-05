"""Translated documents and the English sources they were translated from.

English is the source. Each language mirrors the repository under
`docs/langs/<lang>/`, by the same path, so a translation's path alone says
which file it belongs to. Its first line is the SHA-256 of the source's bytes
as they were when it was translated: the hash changes exactly when the source
does, which is exactly when the translation goes stale. A date moves with
`touch` and a rebase, a commit with any change in the repository.
"""

from py_checks.translations._constants import HOME, SECTION
from py_checks.translations._errors import TranslationError
from py_checks.translations._settings import TranslationsSettings
from py_checks.translations._stamp import fingerprint, stamp, stamped
from py_checks.translations._tree import dead, selected, source_of, tracked, translation_of

__all__ = [
    "HOME",
    "SECTION",
    "TranslationError",
    "TranslationsSettings",
    "dead",
    "fingerprint",
    "selected",
    "source_of",
    "stamp",
    "stamped",
    "tracked",
    "translation_of",
]
