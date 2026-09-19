"""Эффекты: что код берёт у мира и что он о мире говорит.

Часы, случайность и новый идентификатор берутся портом, а не глобальной
функцией: иначе один и тот же вход даёт разный выход, и тест либо замораживает
мир мокой, либо не утверждает ничего. Строка лога называет событие членом
перечисления: это имя читает не человек, а счётчик и алерт.
"""

from py_checks.checks.effects._determinism import Determinism, DeterminismSettings
from py_checks.checks.effects._log_events import LogEvents, LogEventsSettings
from py_checks.checks.effects._marker import MARKER

__all__ = [
    "MARKER",
    "Determinism",
    "DeterminismSettings",
    "LogEvents",
    "LogEventsSettings",
]
