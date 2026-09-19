"""Пример файла окружения, собранный из классов настроек проекта.

Имя переменной знает поле — оно объявляет его `validation_alias`, и правило
`config-fields` за этим следит. Значит, список переменных выводится из тех же
классов, что их читают, и файл, который его перечисляет, нет смысла вести
рукой: он расходится молча, а замечают это, когда переменной не оказалось на
проде.
"""

from py_checks.environment._constants import FILE, SECTION
from py_checks.environment._render import render
from py_checks.environment._settings import Example, example

__all__ = ["FILE", "SECTION", "Example", "example", "render"]
