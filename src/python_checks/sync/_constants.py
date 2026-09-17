"""Имена, общие для всей синхронизации конфигов."""

from __future__ import annotations

from typing import Final

# Папка проекта, в которой лежат копии эталонов. Всё, что в ней, принадлежит
# библиотеке: руками там делать нечего, следующий sync перезапишет.
DIRECTORY: Final = ".python-checks"

PACKAGE: Final = "python_checks.configs"
