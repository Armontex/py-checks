"""A dependency has a ceiling, otherwise the resolver chooses the version."""

from __future__ import annotations

import re
import tomllib
from typing import TYPE_CHECKING, Any, ClassVar, Final

from py_checks.checks.hygiene._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

CODE: Final = "dependency-bounds"

MANIFEST: Final = "pyproject.toml"
MARKERS: Final = ";"
FIRST: Final = 1

# A name followed by extras and specifiers. `packaging` would parse this
# properly and is not a dependency of the hooks, while the forms found in a
# manifest are narrow enough that the expression states the whole rule.
REQUIREMENT: Final = re.compile(
    r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)(?:\[[^\]]*\])?(?P<rest>.*)$"
)


class DependencyBoundsSettings(CheckSettings):
    ceilings: tuple[str, ...] = ("==", "<=", "<", "~=", "===")
    pins: tuple[str, ...] = ("rev", "tag")


class DependencyBounds:
    """Fails when a dependency may move to a version nobody has ever run.

    A requirement declares a ceiling one of two ways: an exact version
    (`greenlet==3.5.5`) or a floor-and-ceiling pair (`pydantic>=2.13.5,<3`;
    `structlog~=26.1` is the same thing said differently).

    A bare floor is refused — `pre-commit>=4.6.2`. It reads as a minimum and
    behaves as "whatever is newest the moment somebody rebuilt the lock", that
    is, as a different service after every rebuild: a major comes out, the
    lock moves, and the change arrives in whichever commit happened to touch
    the dependencies. A ceiling makes that arrival a deliberate edit, with a
    diff behind it and a test run — the only place a breaking upgrade can be
    read at all.

    The lock does not replace this: `uv.lock` pins what is installed today and
    is rebuilt — a constraint is what survives the rebuild.

    Every group is checked: a test dependency decides whether the suite
    passes, and a build one whether a wheel exists at all.

    There is one exception, and it carries its own nail: a requirement with no
    specifiers whose name is in `[tool.uv.sources]` with a `rev` or a `tag`.
    A commit is the tightest ceiling there is.

    Settings: `ceilings`, `pins`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = DependencyBoundsSettings
    scope: ClassVar[Scope] = Scope.PROJECT
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        root: Path,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=DependencyBoundsSettings,
            code=CODE,
        )
        path = root / MANIFEST
        if not path.is_file():
            return
        text = path.read_text(encoding="utf-8")
        manifest = tomllib.loads(text)
        exempt = cls._pinned(
            manifest=manifest,
            pins=limits.pins,
        )
        for where, requirement in cls._requirements(manifest=manifest):
            if cls._bounded(
                requirement=requirement,
                ceilings=limits.ceilings,
                exempt=exempt,
            ):
                continue
            yield Violation(
                path=path,
                line=cls._line(
                    text=text,
                    requirement=requirement,
                ),
                column=FIRST,
                code=CODE,
                message=(
                    f"{where}: {requirement!r} has no ceiling; pin it (==) or bound it "
                    f"(>=x,<y), otherwise the resolver chooses the version"
                ),
            )

    @classmethod
    def _bounded(
        cls,
        *,
        requirement: str,
        ceilings: tuple[str, ...],
        exempt: frozenset[str],
    ) -> bool:
        stated = cls._stated(requirement=requirement)
        if stated is None:
            return True
        if any(ceiling in stated for ceiling in ceilings):
            return True
        return not stated and cls._name(requirement=requirement) in exempt

    @staticmethod
    def _stated(*, requirement: str) -> str | None:
        """The requirement's specifiers, or None if it is not what we read.

        Markers are cut off first: `; python_version < "3.13"` carries its own
        comparison operators and says nothing about which version gets installed.
        """
        written = requirement.split(MARKERS, maxsplit=1)[0].strip()
        found = REQUIREMENT.match(written)
        return None if found is None else found.group("rest").strip()

    @staticmethod
    def _name(*, requirement: str) -> str:
        found = REQUIREMENT.match(requirement.split(MARKERS, maxsplit=1)[0].strip())
        return "" if found is None else found.group("name").lower().replace("_", "-")

    @staticmethod
    def _pinned(
        *,
        manifest: dict[str, Any],
        pins: tuple[str, ...],
    ) -> frozenset[str]:
        """Names whose source is a commit: a ceiling of exactly one version."""
        sources = manifest.get("tool", {}).get("uv", {}).get("sources", {})
        return frozenset(
            name.lower().replace("_", "-")
            for name, source in sources.items()
            if isinstance(source, dict) and any(pin in source for pin in pins)
        )

    @staticmethod
    def _requirements(*, manifest: dict[str, Any]) -> list[tuple[str, str]]:
        """Every requirement in the file, with the group it is written in."""
        project = manifest.get("project", {})
        listed: list[tuple[str, str]] = [
            ("project.dependencies", one) for one in project.get("dependencies", [])
        ]
        for extra, group in project.get("optional-dependencies", {}).items():
            listed += [(f"project.optional-dependencies.{extra}", one) for one in group]
        for name, group in manifest.get("dependency-groups", {}).items():
            # A group may include another group — that is a dict, not a
            # requirement, and there is nothing in it to bound.
            listed += [(f"dependency-groups.{name}", one) for one in group if isinstance(one, str)]
        listed += [
            ("build-system.requires", one)
            for one in manifest.get("build-system", {}).get("requires", [])
        ]
        return listed

    @staticmethod
    def _line(
        *,
        text: str,
        requirement: str,
    ) -> int:
        """The line the requirement is written on: tomllib does not report positions."""
        for number, line in enumerate(text.splitlines(), start=FIRST):
            if requirement in line:
                return number
        return FIRST
