"""Какие конфиги библиотека держит у себя."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from python_checks.sync._constants import DIRECTORY


@dataclass(frozen=True, slots=True)
class Managed:
    """Эталонный файл и то, чем его подключает проект.

    `stub` пишется один раз — когда конфига проекта ещё нет. Дальше он
    принадлежит проекту целиком: послабления, исключённые папки и всё
    остальное, что у каждого своё.
    """

    name: str
    project: str
    section: str
    stub: str


RUFF: Final = Managed(
    name="ruff.toml",
    project="ruff.toml",
    section="ruff",
    stub=f"""\
extend = "{DIRECTORY}/ruff.toml"

# Дальше — проектное: послабления по папкам и всё, чего нет у остальных.
[lint.per-file-ignores]
"tests/*" = ["S101"]
""",
)

PYRIGHT: Final = Managed(
    name="pyrightconfig.json",
    project="pyrightconfig.json",
    section="pyright",
    stub=f"""\
{{
  "extends": "{DIRECTORY}/pyrightconfig.json",
  "include": ["src", "tests"],
  "venvPath": ".",
  "venv": ".venv"
}}
""",
)

MANAGED: Final[tuple[Managed, ...]] = (RUFF, PYRIGHT)
