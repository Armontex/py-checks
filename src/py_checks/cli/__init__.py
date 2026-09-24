"""The command line.

The entry point pre-commit calls the checks through, and the commands for a
manual run: run the checks, show the list, explain a rule.
"""

from py_checks.cli._app import app, main
from py_checks.cli._protocols import Registrar

__all__ = ["Registrar", "app", "main"]
