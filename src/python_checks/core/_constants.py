"""Имена и коды, общие для ядра."""

from __future__ import annotations

from typing import Final

# Группа entry points, в которой объявляются проверки: своя проверка живёт в
# отдельном пакете и не требует форка библиотеки.
GROUP: Final = "python_checks.checks"

# Что видит оболочка. Голая единица была бы кодом, смысл которого знает только
# вызывающий; pre-commit по ней останавливает коммит.
EXIT_OK: Final = 0
EXIT_VIOLATION: Final = 1
