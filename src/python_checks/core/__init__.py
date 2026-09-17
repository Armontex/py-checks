"""Общая часть всех проверок.

Поиск файлов, разбор исходника один раз на файл, описание нарушения, реестр
проверок и вывод. Правило знает только своё условие, всё остальное берёт
отсюда.
"""

from python_checks.core._constants import EXIT_OK, EXIT_VIOLATION, GROUP
from python_checks.core._discovery import python_files
from python_checks.core._errors import ParseError, UnknownCheckError
from python_checks.core._protocols import FileCheck
from python_checks.core._registry import available, get
from python_checks.core._report import report
from python_checks.core._source import ParsedFile
from python_checks.core._violation import Violation

__all__ = [
    "EXIT_OK",
    "EXIT_VIOLATION",
    "GROUP",
    "FileCheck",
    "ParseError",
    "ParsedFile",
    "UnknownCheckError",
    "Violation",
    "available",
    "get",
    "python_files",
    "report",
]
