"""Словарь отказов пакета в одном месте."""


class OrderError(Exception):
    """Корень отказов модуля."""


class OrderNotFound(OrderError):
    """Наследник своего корня, а не Exception."""
