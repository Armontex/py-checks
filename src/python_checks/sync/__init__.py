"""Эталонные конфиги в проекте.

Общая часть настроек ruff и pyright живёт в библиотеке, а `sync` кладёт её
копию в `.python-checks/` проекта. Конфиг проекта подключает копию (`extend`,
`extends`) и держит рядом только своё.

Копия лежит в репозитории, а не читается из окружения: ruff и pyright — чужие
программы, путь внутрь `site-packages` на каждой машине свой, а конфиг нужен и
в CI, и у того, кто библиотеку ещё не поставил.
"""

from python_checks.sync._canonical import canonical
from python_checks.sync._constants import DIRECTORY, PACKAGE
from python_checks.sync._leftovers import leftovers
from python_checks.sync._managed import MANAGED, Managed
from python_checks.sync._sync import stale, write

__all__ = [
    "DIRECTORY",
    "MANAGED",
    "PACKAGE",
    "Managed",
    "canonical",
    "leftovers",
    "stale",
    "write",
]
