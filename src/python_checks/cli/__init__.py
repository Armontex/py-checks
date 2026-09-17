"""Командная строка.

Точка входа, через которую проверки вызывает pre-commit, и команды для ручного
запуска: прогнать проверки, показать список, объяснить правило.
"""

from python_checks.cli._app import app, main
from python_checks.cli._protocols import Registrar

__all__ = ["Registrar", "app", "main"]
