"""Files the library builds for the project.

Today there are two: the import contracts for import-linter and
`.env.example`. The library does not touch the settings of ruff, pyright and
the other tools: the template brings them, and from then on they belong to
the project, which edits them as it sees fit.

What gets built is what cannot be written once: a layer missing from disk
breaks the whole import-linter run, and the layout changes over a project's
life; the list of variables lives in the fields of the settings classes, and
a file kept beside them by hand drifts from them silently.
"""

from py_checks.sync._sync import planned, stale, write

__all__ = ["planned", "stale", "write"]
