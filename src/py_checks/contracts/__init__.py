"""Контракты импортов для import-linter.

Как называются слои и кому что можно — знает проект, а не библиотека: в
сервисе это `domain` и `presentation`, в утилите — `core` и `cli`, и придумать
за них нельзя. Проект описывает это в `[tool.py-checks.contracts]`, а
`py-checks sync` собирает контракты под его раскладку: слои, которых на
диске нет, в файл не попадают, иначе import-linter упал бы на первом же
несуществующем модуле.

Собранный файл править нечего — перезапишет следующий sync; менять нужно
секцию.
"""

from py_checks.contracts._constants import FILE, MIGRATIONS, MODULES, SECTION
from py_checks.contracts._render import render
from py_checks.contracts._settings import Contracts, contracts

__all__ = [
    "FILE",
    "MIGRATIONS",
    "MODULES",
    "SECTION",
    "Contracts",
    "contracts",
    "render",
]
