"""Сигнатуры и тела.

Длина модуля и требование писать сигнатуру полностью. Вложенность, число
аргументов, длина функции и перенос аргументов закрываются правилами ruff.
"""

from python_checks.checks.signatures._module_length import ModuleLength, ModuleLengthSettings

__all__ = ["ModuleLength", "ModuleLengthSettings"]
