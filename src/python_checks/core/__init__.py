"""Общая часть всех проверок.

Поиск файлов, разбор исходника один раз на файл, описание нарушения, реестр
проверок и вывод. Правило знает только своё условие, всё остальное берёт
отсюда.
"""

from python_checks.core._constants import EXIT_OK, EXIT_VIOLATION, GROUP, PROJECT_GROUP
from python_checks.core._discovery import python_files
from python_checks.core._edit import Edit, apply, column
from python_checks.core._errors import ParseError, UnknownCheckError
from python_checks.core._fixer import fix
from python_checks.core._format import reformat
from python_checks.core._markers import MARKER, Marker, complaints, read, surviving
from python_checks.core._protocols import Check, FileCheck, ProjectCheck
from python_checks.core._registry import available, available_project, get, get_project
from python_checks.core._report import report
from python_checks.core._runner import SYNTAX, examine, inspect
from python_checks.core._settings import SettingsMismatchError, settings_as
from python_checks.core._source import ParsedFile
from python_checks.core._violation import Violation

__all__ = [
    "EXIT_OK",
    "EXIT_VIOLATION",
    "GROUP",
    "PROJECT_GROUP",
    "MARKER",
    "SYNTAX",
    "Edit",
    "Check",
    "FileCheck",
    "ProjectCheck",
    "Marker",
    "ParseError",
    "ParsedFile",
    "SettingsMismatchError",
    "UnknownCheckError",
    "Violation",
    "apply",
    "available",
    "available_project",
    "column",
    "complaints",
    "fix",
    "examine",
    "get",
    "get_project",
    "inspect",
    "python_files",
    "read",
    "reformat",
    "surviving",
    "settings_as",
    "report",
]
