"""The project-wide settings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Final

from pydantic import Field, ValidationError

from py_checks.config._base import CheckSettings
from py_checks.config._constants import DEFAULT_EXCLUDE, PYPROJECT, SECTION
from py_checks.config._errors import ConfigError
from py_checks.config._toml import TomlTable

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True, slots=True)
class Moved:
    """Where a section moved to, and how it is written there."""

    into: str
    written: str


# Sections that are no longer read. Keeping quiet about them is not an option:
# an unknown section looks like a working setting, while the rule actually
# judges by an empty table.
#
# Four layout rules described one directory from four sides, and one fact had
# to be written four times in four syntaxes. `endpoint-declarations` moved for
# the same reason from the other end: the route turned out not to be the only
# entrance into the process, and a second kind of entrance does not fit into a
# flat section.
RETIRED: Final[dict[str, Moved]] = {
    "class-modules": Moved(
        into="layout",
        written="`only`",
    ),
    "class-placement": Moved(
        into="layout",
        written="`home` and `suffix`",
    ),
    "required-class": Moved(
        into="layout",
        written="`required` next to `suffix`",
    ),
    "operation-shape": Moved(
        into="layout",
        written="`operation`",
    ),
    "model-boundary": Moved(
        into="layout",
        written="`orm` and `base`",
    ),
    "endpoint-declarations": Moved(
        into="edge-declarations",
        written="a block per kind of entrance — `route` with the same keys",
    ),
}


def retired(
    *,
    checks: Mapping[str, object],
    source: Path | None,
) -> None:
    """Fails if the settings still hold sections that were merged into shared tables."""
    found = sorted(name for name in RETIRED if name in checks)
    if not found:
        return
    named = prefix(source=source)
    listed = "; ".join(
        f"[{named}{name}] -> [{named}{RETIRED[name].into}], {RETIRED[name].written}"
        for name in found
    )
    raise ConfigError(
        f"these sections are no longer read, their content moved into shared tables, "
        f"one block per subject: {listed}"
    )


def prefix(*, source: Path | None) -> str:
    """What a check's section is called in the file the settings came from.

    In `pyproject.toml` tools live under their own prefix, because the file is
    shared; in the tool's own file there is no prefix — the whole file belongs
    to one tool. An error message must name the section the way it is actually
    named in that file: otherwise it sends the reader to the wrong place.
    """
    if source is None or source.name == PYPROJECT:
        return f"tool.{SECTION}."
    return ""


class Config(CheckSettings):
    """Where to look for code and what not to check.

    The settings of the checks themselves do not land here: they sit in their
    own sections and are parsed by the model of the check they belong to. The
    core keeps them untouched in `checks` and hands them to the owner through
    `settings_for`.
    """

    src: Path = Path("src")
    exclude: tuple[str, ...] = DEFAULT_EXCLUDE
    extend_exclude: tuple[str, ...] = ()
    ignore: tuple[str, ...] = ()
    checks: dict[str, TomlTable] = Field(
        default_factory=dict,
        exclude=True,
    )
    # The file the settings were read from: it is also where an error message
    # sends the reader.
    origin: Path | None = Field(
        default=None,
        exclude=True,
    )

    @property
    def excluded(self) -> tuple[str, ...]:
        """What is not checked: the default list plus what the project added.

        `exclude` sets the whole list, `extend-exclude` adds to it: that way a
        project adds its own folder without rewriting `.venv` and the rest.
        """
        return self.exclude + self.extend_exclude

    def section(self, *, code: str) -> TomlTable:
        return self.checks.get(code, {})

    def settings_for(
        self,
        *,
        code: str,
        model: type[CheckSettings],
    ) -> CheckSettings:
        """A check's settings: its section, validated by its own model."""
        try:
            return model.model_validate(self.section(code=code))
        except ValidationError as error:
            raise ConfigError(f"[{prefix(source=self.origin)}{code}]: {error}") from error

    def enabled(self, *, code: str) -> bool:
        return code not in self.ignore
