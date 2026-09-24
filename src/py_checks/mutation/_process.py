"""Running external commands: mutmut and git."""

from __future__ import annotations

import os
import subprocess  # noqa: S404 — calling mutmut is what the gate does
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from py_checks.mutation._errors import GateError

if TYPE_CHECKING:
    from pathlib import Path


@dataclass(frozen=True, slots=True)
class Shell:
    """Where and with which environment the gate's commands run."""

    root: Path
    env: dict[str, str] = field(default_factory=dict[str, str])

    def finished(self, *, command: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        return subprocess.run(  # noqa: S603 — a list of arguments, no shell
            command,
            cwd=self.root,
            capture_output=True,
            text=True,
            check=False,
            env=os.environ | self.env,
        )

    def answered(self, *, command: tuple[str, ...]) -> str:
        """The output of a command that must succeed; otherwise a refusal in its own words."""
        finished = self.finished(command=command)
        if finished.returncode:
            raise GateError(said(finished=finished))
        return finished.stdout


def said(*, finished: subprocess.CompletedProcess[str]) -> str:
    """What the tool said, so that a refusal names its reason."""
    words = finished.stderr.strip() or finished.stdout.strip()
    return f"`{' '.join(finished.args)}` exited with code {finished.returncode}\n{words}"
