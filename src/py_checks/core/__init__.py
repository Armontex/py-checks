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
from py_checks.core._markers import MARKER, Marker, complaints, read, surviving
from py_checks.core._protocols import Check, FileCheck, ProjectCheck, Scope
from py_checks.core._registry import Checks, available, get
from py_checks.core._report import report
from py_checks.core._runner import SYNTAX, examine, inspect, survey
from py_checks.core._settings import SettingsMismatchError, settings_as
from py_checks.core._source import ParsedFile
from py_checks.core._violation import Violation

__all__ = [
    "EXIT_OK",
    "EXIT_VIOLATION",
    "GROUP",
    "MARKER",
    "SYNTAX",
    "Check",
    "Checks",
    "Edit",
    "FileCheck",
    "ProjectCheck",
    "Marker",
    "ParseError",
    "ParsedFile",
    "Scope",
    "SettingsMismatchError",
    "UnknownCheckError",
    "Violation",
    "apply",
    "available",
    "column",
    "complaints",
    "fix",
    "examine",
    "get",
    "inspect",
    "python_files",
    "read",
    "reformat",
    "surviving",
    "settings_as",
    "report",
    "survey",
]
