"""Запись выживших по модулям: с ней сравнивают, её пишет `record`."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from py_checks.mutation._errors import GateError

if TYPE_CHECKING:
    from pathlib import Path


def recorded(*, path: Path) -> dict[str, int]:
    """Сколько выживших числится за каждым модулем.

    Записи, которой ещё нет, соответствует пустая: это правда о проекте, чей
    первый модуль ещё не написан.
    """
    if not path.is_file():
        return {}
    read: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(read, dict) or not all(
        isinstance(count, int)
        for count in read.values()  # pyright: ignore[reportUnknownVariableType]
    ):
        raise GateError(f"{path}: ожидался объект «модуль → число выживших»")
    return {str(module): int(count) for module, count in read.items()}  # pyright: ignore[reportUnknownVariableType, reportUnknownArgumentType]


def write(
    *,
    path: Path,
    counted: dict[str, int],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    path.write_text(
        json.dumps(
            dict(sorted(counted.items())),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
