"""Общая часть всех проверок.

Поиск файлов, разбор исходника один раз на файл, описание нарушения, реестр
проверок и вывод. Правило знает только своё условие, всё остальное берёт
отсюда.
"""

from python_checks.core._constants import EXIT_OK, EXIT_VIOLATION, GROUP
from python_checks.core._discovery import python_files
from python_checks.core._edit import Edit, apply, column
from python_checks.core._errors import ParseError, UnknownCheckError
from python_checks.core._fixer import fix
from python_checks.core._format import reformat
from python_checks.core._markers import MARKER, Marker, complaints, read, surviving
from python_checks.core._protocols import Check, FileCheck, ProjectCheck, Scope
from python_checks.core._registry import Checks, available, get
from python_checks.core._report import report
from python_checks.core._runner import SYNTAX, examine, inspect, survey
from python_checks.core._settings import SettingsMismatchError, settings_as
from python_checks.core._source import ParsedFile
from python_checks.core._violation import Violation

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
