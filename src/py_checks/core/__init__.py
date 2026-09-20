"""Общая часть всех проверок.

Поиск файлов, разбор исходника один раз на файл, описание нарушения, реестр
проверок и вывод. Правило знает только своё условие, всё остальное берёт
отсюда.
"""

from py_checks.core._constants import EXIT_OK, EXIT_VIOLATION, GROUP
from py_checks.core._discovery import python_files
from py_checks.core._edit import Edit, apply, column
from py_checks.core._errors import ParseError, UnknownCheckError
from py_checks.core._fixer import fix
from py_checks.core._format import reformat
from py_checks.core._markers import MARKER, Marker, complaints, markers, surviving
from py_checks.core._protocols import Check, FileCheck, ProjectCheck, Scope
from py_checks.core._registry import Checks, available, get
from py_checks.core._report import report
from py_checks.core._runner import SYNTAX, examine, inspect, survey
from py_checks.core._settings import SettingsMismatchError, settings_as
from py_checks.core._source import ParsedFile
from py_checks.core._violation import Violation

__all__ = [
    "Check",
    "Checks",
    "EXIT_OK",
    "EXIT_VIOLATION",
    "Edit",
    "FileCheck",
    "GROUP",
    "MARKER",
    "Marker",
    "ParseError",
    "ParsedFile",
    "ProjectCheck",
    "SYNTAX",
    "Scope",
    "SettingsMismatchError",
    "UnknownCheckError",
    "Violation",
    "apply",
    "available",
    "column",
    "complaints",
    "examine",
    "fix",
    "get",
    "inspect",
    "markers",
    "python_files",
    "reformat",
    "report",
    "settings_as",
    "survey",
    "surviving",
]
