"""Размещение и форма модуля.

Где лежит класс, что допускает директория, какой класс модуль обязан объявить
первым. Соглашения, привязанные к раскладке директорий: готовых инструментов
под них нет — семейство ArchUnit для Python занято импортами, а движки образцов
(Semgrep, ast-grep) умеют запрещать, но не разрешать.

Таблицы проектные: имена `use_cases`, `dto`, `schemas` библиотека знать не
может. Без них правила молчат.
"""

from python_checks.checks.placement._class_modules import ClassModules, ClassModulesSettings
from python_checks.checks.placement._marker import MARKER

__all__ = ["MARKER", "ClassModules", "ClassModulesSettings"]
