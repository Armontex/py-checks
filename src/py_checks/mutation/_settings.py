"""The `[mutation]` section: how to call mutmut and what to compare against."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import Field, ValidationError

from py_checks.config import CheckSettings, ConfigError, prefix
from py_checks.mutation._constants import BASELINE, SECTION

if TYPE_CHECKING:
    from py_checks.config import Config


class Mutation(CheckSettings):
    """The `[tool.py-checks.mutation]` section.

    `command` — how to call mutmut. By default from the same environment as
    the library itself; a list, not a string, so that no shell splits the
    arguments.

    `baseline` — the file `record` writes the survivors per module to. Both
    `diff` and `full` compare against it.

    `against` — what to compare the branch with when the push has not said:
    the first name this clone knows.

    `children` — how many mutants to check at once. Empty — mutmut decides.

    `env` — variables for the run. The typical one is a hypothesis profile: a
    property that draws new examples every time kills a mutant in one run and
    misses it in the next, and the record starts moving on its own.

    What to mutate is not said here: that is `source_paths` and
    `do_not_mutate` of mutmut itself, and the gate reads them from wherever
    mutmut does.
    """

    command: tuple[str, ...] = ("mutmut",)
    baseline: str = BASELINE
    against: tuple[str, ...] = ("origin/develop", "develop")
    children: int | None = Field(
        default=None,
        gt=0,
    )
    env: dict[str, str] = Field(default_factory=dict)


def mutation(*, config: Config) -> Mutation:
    try:
        return Mutation.model_validate(config.section(code=SECTION))
    except ValidationError as error:
        raise ConfigError(f"[{prefix(source=config.origin)}{SECTION}]: {error}") from error
