"""Типы значений, какими их отдаёт `tomllib`."""

from __future__ import annotations

import datetime

type TomlValue = (
    bool
    | int
    | float
    | str
    | datetime.datetime
    | datetime.date
    | datetime.time
    | list[TomlValue]
    | TomlTable
)

type TomlTable = dict[str, TomlValue]
"""Таблица TOML: секция конфига до того, как её разобрала модель.

Не `dict[str, Any]`: `Any` отключает проверку типов у всех, кто такую таблицу
получит, а здесь заранее известно, что значения бывают ровно этих видов.
"""
