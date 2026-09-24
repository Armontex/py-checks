"""The settings classes the environment example is built from."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import ValidationError

from py_checks.config import CheckSettings, ConfigError, prefix
from py_checks.environment._constants import FILE, SECTION

if TYPE_CHECKING:
    from py_checks.config import Config


class Example(CheckSettings):
    """The `[tool.py-checks.env-example]` section.

    `settings` — the settings classes, each as `module:Class`. It is the
    sections that are listed, not one root class: the root builds them with
    factories, and its own fields are sections, not variables. An empty list
    means "build nothing": a project with no settings from the environment is
    an ordinary thing.

    `path` — where to write; `.env.example` in the root by default.

    `header` — the file's own header text, `#` included. An empty string keeps
    the library's header: a project that writes its comments in another
    language needs its own, the rest do not.
    """

    settings: tuple[str, ...] = ()
    path: str = FILE
    header: str = ""


def example(*, config: Config) -> Example:
    try:
        return Example.model_validate(config.section(code=SECTION))
    except ValidationError as error:
        raise ConfigError(f"[{prefix(source=config.origin)}{SECTION}]: {error}") from error
