"""The commands, one module per command.

A command's module knows its own name and its own options: `_app` only builds
the application from their `register`. When a command grows subcommands, its
`register` will call `add_typer`, and the building code will not notice.
"""

from typing import Final

from py_checks.cli._protocols import Registrar
from py_checks.cli.commands._doctor import register as register_doctor
from py_checks.cli.commands._explain import register as register_explain
from py_checks.cli.commands._list import register as register_list
from py_checks.cli.commands._mutation import register as register_mutation
from py_checks.cli.commands._run import register as register_run
from py_checks.cli.commands._sync import register as register_sync

REGISTRARS: Final[tuple[Registrar, ...]] = (
    register_run,
    register_list,
    register_explain,
    register_sync,
    register_doctor,
    register_mutation,
)

__all__ = ["REGISTRARS", "Registrar"]
