"""Команды, по модулю на команду.

Модуль команды сам знает своё имя и свои опции: `_app` только собирает
приложение из их `register`. Когда у команды появятся подкоманды, её `register`
вызовет `add_typer`, и собирающий код это не заметит.
"""

from typing import Final

from python_checks.cli._protocols import Registrar
from python_checks.cli.commands._explain import register as register_explain
from python_checks.cli.commands._list import register as register_list
from python_checks.cli.commands._run import register as register_run
from python_checks.cli.commands._sync import register as register_sync

REGISTRARS: Final[tuple[Registrar, ...]] = (
    register_run,
    register_list,
    register_explain,
    register_sync,
)

__all__ = ["REGISTRARS", "Registrar"]
