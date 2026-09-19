"""Размещение и форма модуля.

Где лежит класс, что допускает директория, какой класс модуль обязан объявить
первым. Соглашения, привязанные к раскладке директорий: готовых инструментов
под них нет — семейство ArchUnit для Python занято импортами, а движки образцов
(Semgrep, ast-grep) умеют запрещать, но не разрешать.

Таблицы проектные: имена `use_cases`, `dto`, `schemas` библиотека знать не
может. Без них правила молчат.
"""

from py_checks.checks.placement._class_modules import ClassModules, ClassModulesSettings
from py_checks.checks.placement._class_placement import (
    ClassPlacement,
    ClassPlacementSettings,
    Rule,
)
from py_checks.checks.placement._marker import MARKER
from py_checks.checks.placement._operation_shape import (
    Operation,
    OperationShape,
    OperationShapeSettings,
)
from py_checks.checks.placement._required_class import RequiredClass, RequiredClassSettings

__all__ = [
    "MARKER",
    "ClassModules",
    "ClassModulesSettings",
    "ClassPlacement",
    "ClassPlacementSettings",
    "Operation",
    "OperationShape",
    "OperationShapeSettings",
    "RequiredClass",
    "RequiredClassSettings",
    "Rule",
]
