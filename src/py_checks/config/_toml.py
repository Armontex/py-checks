"""The value types as `tomllib` returns them."""

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
"""A TOML table: a config section before a model has parsed it.

Not `dict[str, Any]`: `Any` switches off type checking for everyone who gets
such a table, while here it is known in advance that values are of exactly
these kinds.
"""
