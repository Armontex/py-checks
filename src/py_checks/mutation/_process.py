"""Запуск внешних команд: mutmut и git."""

from __future__ import annotations

import os
import subprocess  # noqa: S404 — гейт состоит в том, чтобы позвать mutmut
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from py_checks.mutation._errors import GateError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Shell:
    """Где и с каким окружением запускаются команды гейта."""

    root: Path
    env: dict[str, str] = field(default_factory=dict[str, str])

    def finished(self, *, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 — список аргументов, без шелла
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ | self.env,
        )

    def answered(self, *, command: tuple[str, ...]) -> str:
        """Вывод команды, которая обязана пройти; иначе — отказ с её словами."""
        finished = self.finished(command=command)
        if finished.returncode:
            raise GateError(said(finished=finished))
        return finished.stdout


def said(*, finished: subprocess.CompletedProcess[str]) -> str:
    """Что сказал инструмент, чтобы отказ назвал свою причину."""
    words = finished.stderr.strip() or finished.stdout.strip()
    return f"`{' '.join(finished.args)}` завершился с кодом {finished.returncode}\n{words}"
