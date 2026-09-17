"""Форматирование файлов, которые правил автофикс."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

FORMATTER: Final = "ruff"


def reformat(*, paths: Sequence[Path]) -> None:
    """Пройтись форматтером по изменённым файлам.

    Правка ставит символы, а не колонки: после вставки `*` подпись может стать
    длиннее лимита строки. Раскладывать её руками — работа форматтера, он в
    проекте всё равно есть. Если его нет, файл остаётся исправленным, просто
    неотформатированным.
    """
    formatter = shutil.which(FORMATTER)
    if formatter is None or not paths:
        return
    subprocess.run(  # noqa: S603 - команда своя, пути берутся из найденных файлов
        [formatter, "format", "--quiet", *(str(path) for path in paths)],
        check=False,
    )
