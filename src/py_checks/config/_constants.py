"""Names and defaults shared by all of the settings reading."""

from __future__ import annotations

from typing import Final

PYPROJECT: Final = "pyproject.toml"

SECTION: Final = "py-checks"

# The tool's own settings file — as with ruff and mypy: named after the tool,
# with or without a leading dot. It has no `[tool.py-checks]` prefix: the whole
# file is that section, and `[<code>]` in it is a check's section.
#
# There are four names: the full and the short one, each with and without the
# dot. Guessing what a project will call its file is cheaper than refusing it
# over the wrong letter — and two files at once are forbidden anyway.
STANDALONE: Final[tuple[str, ...]] = (
    ".py-checks.toml",
    "py-checks.toml",
    ".pychecks.toml",
    "pychecks.toml",
)

DEFAULT_EXCLUDE: Final[tuple[str, ...]] = (
    ".venv/*",
    "build/*",
    "dist/*",
    "**/__pycache__/*",
    "**/migrations/versions/*",
)
