"""Контракты импортов для import-linter.

Таблица слоёв — чей импорт куда разрешён — живёт здесь, а не в четырёх
проектах. `python-checks sync` собирает из неё файл контрактов под раскладку
конкретного проекта: слои, которых на диске нет, в контракты не попадают,
иначе import-linter упал бы на первом же несуществующем модуле.

Проект, у которого слой свой (`workflows` в trading), перечисляет отличие в
`[tool.python-checks.layers]`, а не правит собранный файл: его перезапишет
следующий sync.
"""

from python_checks.contracts._base import BASE, COMPOSITION_ROOT
from python_checks.contracts._constants import FILE, MIGRATIONS, MODULES, SECTION
from python_checks.contracts._render import render
from python_checks.contracts._settings import Override, layers

__all__ = [
    "BASE",
    "COMPOSITION_ROOT",
    "FILE",
    "MIGRATIONS",
    "MODULES",
    "SECTION",
    "Override",
    "layers",
    "render",
]
