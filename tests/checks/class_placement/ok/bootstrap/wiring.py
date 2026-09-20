"""Сборка приложения: dataclass здесь — способ сложить три поля рядом."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Wiring:
    """Ни dto, ни value object: соглашение про `dto` сюда не дотягивается."""

    host: str
    port: int
