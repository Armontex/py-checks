"""Сценарий знает про контейнер и про веб-стек."""

from dishka import FromDishka  # import-ok: так его объявляет dishka
from fastapi import Depends

__all__ = ["Depends", "FromDishka"]
