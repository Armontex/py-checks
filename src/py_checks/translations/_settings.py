"""The `[translations]` section."""

from __future__ import annotations

from py_checks.config import CheckSettings


class TranslationsSettings(CheckSettings):
    """Which documents are translated, and into what.

    `langs` — the languages, each a directory under `docs/langs/`.
    `files` — the documents that need a translation, in gitignore syntax: the
    last match wins, and `!` takes a file back out. A directory is excluded
    with what is under it, `!.github/**`; `!.github/` excludes the directory
    itself, and a `*.md` still matches every file inside it.

    Either one empty, and the rule is silent: which documents a project
    translates, and into what, only the project knows.
    """

    langs: tuple[str, ...] = ()
    files: tuple[str, ...] = ()
