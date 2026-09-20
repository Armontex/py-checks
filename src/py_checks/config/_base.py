"""Базовая модель настроек проверки."""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict


def _to_kebab(name: str) -> str:  # check-ok: keyword-only-arguments: pydantic зовёт по позиции
    return name.replace("_", "-")


class CheckSettings(BaseModel):
    """Настройки одной проверки из её секции в `pyproject.toml`.

    В файле ключи пишутся через дефис (`max-lines`), в коде — через
    подчёркивание. `extra="forbid"` нужен, чтобы опечатка падала сразу: молча
    проигнорированная настройка — это проверка, которая работает не так, как
    написано в конфиге, и никто об этом не знает.
    """

    model_config = ConfigDict(
        alias_generator=_to_kebab,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


# Таблица, ключи которой приносит проект: имя директории, пакета, конструкции.
# Такое имя — данные, а не поле модели, поэтому `extra` открыт, но значение под
# ним проверяется: модель объявляет `__pydantic_extra__` своим типом.
OPEN: Final[ConfigDict] = CheckSettings.model_config | {"extra": "allow"}
