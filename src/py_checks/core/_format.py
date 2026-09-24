"""Formatting the files the autofix has edited."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

FORMATTER: Final = "ruff"


def reformat(*, paths: Sequence[Path]) -> None:
    """Run the formatter over the changed files.

    An edit places characters, not columns: after `*` is inserted a signature
    may grow past the line limit. Laying it out is the formatter's job, and
    the project has one anyway. If it does not, the file stays fixed, just
    not formatted.
    """
    formatter = shutil.which(FORMATTER)
    if formatter is None or not paths:
        return
    subprocess.run(  # noqa: S603 - our own command, the paths come from the files found
        [formatter, "format", "--quiet", *(str(path) for path in paths)],
        check=False,
    )
