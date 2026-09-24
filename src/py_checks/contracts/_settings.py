"""The project's layers: what it has declared about itself."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from py_checks.config import CheckSettings, ConfigError
from py_checks.contracts._constants import SECTION

if TYPE_CHECKING:
    from py_checks.config import Config


class Contracts(CheckSettings):
    """The `[tool.py-checks.contracts]` section.

    `layers` — a layer and what it may import. Anything missing from the table
    has no restrictions: the library does not know what the layers are called
    in this project and does not guess on its behalf.

    `composition-root` — layers that may import anything: they tie the rest
    together, and that is the whole of their work. They are listed separately
    so that they end up in the others' forbidden lists: a layer the table does
    not know about is forbidden to nobody.

    `header` — the built file's own header text, `#` included. An empty
    string keeps the library's header.
    """

    composition_root: tuple[str, ...] = ()
    layers: dict[str, tuple[str, ...]] = {}
    header: str = ""


def contracts(*, config: Config) -> Contracts:
    try:
        return Contracts.model_validate(config.section(code=SECTION))
    except ValidationError as error:
        raise ConfigError(f"[tool.py-checks.{SECTION}]: {error}") from error
