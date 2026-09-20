"""Размещение и форма модуля.

Где лежит класс, что допускает директория, какой класс модуль обязан объявить
первым. Соглашения, привязанные к раскладке директорий: готовых инструментов
под них нет — семейство ArchUnit для Python занято импортами, а движки образцов
(Semgrep, ast-grep) умеют запрещать, но не разрешать.

Все четыре правила читают общую таблицу `[layout]` — блок на директорию: они
говорят об одном и том же с четырёх сторон, и четыре таблицы об одном
разъезжались бы между собой. Живёт она в `checks/_layout.py`, потому что из
той же таблицы читает и `model-boundary`: раскладка — слово проекта, а не
собственность одной группы правил. Таблица проектная: имена `use_cases`, `dto`,
`schemas` библиотека знать не может. Без неё правила молчат.
"""

from py_checks.checks._layout import SECTION, Directory, Layout, Operation, Orm
from py_checks.checks.placement._class_modules import ClassModules
from py_checks.checks.placement._class_placement import ClassPlacement
from py_checks.checks.placement._marker import MARKER
from py_checks.checks.placement._operation_shape import OperationShape, Shape
from py_checks.checks.placement._required_class import RequiredClass

__all__ = [
    "MARKER",
    "SECTION",
    "ClassModules",
    "ClassPlacement",
    "Directory",
    "Layout",
    "Operation",
    "Orm",
    "OperationShape",
    "RequiredClass",
    "Shape",
]
