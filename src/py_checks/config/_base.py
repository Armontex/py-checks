"""The base model for a check's settings."""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict


def _to_kebab(name: str) -> str:  # check-ok: keyword-only-arguments: pydantic calls it positionally
    return name.replace("_", "-")


class CheckSettings(BaseModel):
    """The settings of one check, from its section in `pyproject.toml`.

    In the file keys are written with hyphens (`max-lines`), in the code with
    underscores. `extra="forbid"` is there so a typo fails at once: a setting
    silently ignored is a check that works differently from what the config
    says, and nobody knows it.
    """

    model_config = ConfigDict(
        alias_generator=_to_kebab,
        populate_by_name=True,
        extra="forbid",
        frozen=True,
    )


# A table whose keys the project brings: the name of a directory, a package, a
# construct. Such a name is data, not a field of the model, so `extra` is open,
# but the value under it is still checked: the model declares
# `__pydantic_extra__` with its own type.
OPEN: Final[ConfigDict] = CheckSettings.model_config | {"extra": "allow"}
