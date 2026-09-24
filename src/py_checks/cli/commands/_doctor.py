"""The `doctor` command: what is wrong with the settings themselves."""

from __future__ import annotations

from collections.abc import Sized
from dataclasses import dataclass
from difflib import get_close_matches
from pathlib import Path
from typing import TYPE_CHECKING, Final

import typer
from rich.console import Console

from py_checks.config import ConfigError, find_root, load, prefix
from py_checks.contracts import SECTION as CONTRACTS
from py_checks.core import EXIT_OK, EXIT_VIOLATION, available, depth, section_of
from py_checks.environment import SECTION as ENV_EXAMPLE
from py_checks.mutation import SECTION as MUTATION

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings, Config, TomlValue
    from py_checks.core import Check

# Sections read by something other than a rule: the file builders and the mutation gate.
OWNED: Final[frozenset[str]] = frozenset({CONTRACTS, ENV_EXAMPLE, MUTATION})

# The key that names places: every rule that does not work everywhere has it,
# and an empty list in it means the rule is silent across the whole tree.
ZONES: Final = "zones"

# How many similar names to offer in answer to a typo, and how similar: the
# difflib default (0.6) stays silent where a person sees the typo by eye.
CLOSE: Final = 2
ALIKE: Final = 0.5

SUFFIX: Final = ".py"

# The field and the reason: the rest of pydantic's complaint is bookkeeping.
REASON: Final = 2


@dataclass(frozen=True, slots=True)
class Complaint:
    """What is wrong, and with what exactly."""

    said: str
    about: str


def doctor() -> None:
    """Check the settings themselves: typos, dead addresses, silent rules."""
    config = load(root=find_root(start=Path.cwd()))
    found = [
        *_unknown(config=config),
        *_ignored(config=config),
        *_silent(config=config),
        *_nowhere(config=config),
    ]
    # A long name is not broken mid-word: the reader will copy it.
    console = Console(soft_wrap=True)
    console.print(f"{config.origin or 'default settings'}\n", markup=False)
    for said, group in _grouped(found=found).items():
        console.print(f"  {said}", markup=False)
        for complaint in group:
            console.print(f"    {complaint.about}", markup=False)
        console.print()
    console.print(_count(found=found), markup=False)
    raise typer.Exit(code=EXIT_VIOLATION if found else EXIT_OK)


def _grouped(*, found: list[Complaint]) -> dict[str, list[Complaint]]:
    """The complaints by heading, in order of first appearance."""
    groups: dict[str, list[Complaint]] = {}
    for complaint in found:
        groups.setdefault(complaint.said, []).append(complaint)
    return groups


def _count(*, found: list[Complaint]) -> str:
    return f"complaint(s): {len(found)}" if found else "ok: the settings hold together"


def _sections() -> set[str]:
    """The names of the sections somebody reads: five rules share one."""
    return {section_of(check=check) for check in available().listed.values()}


def _unknown(*, config: Config) -> Iterator[Complaint]:
    """A section that matches neither a rule nor a builder."""
    known = _sections()
    named = prefix(source=config.origin)
    for section in sorted(config.checks):
        if section in known or section in OWNED:
            continue
        close = get_close_matches(
            section,
            [*known, *OWNED],
            n=CLOSE,
            cutoff=ALIKE,
        )
        said = f"; closest: {', '.join(close)}" if close else ""
        yield Complaint(
            said="typo in a section name",
            about=f"[{named}{section}] — no such section{said}",
        )


def _ignored(*, config: Config) -> Iterator[Complaint]:
    """An `ignore` that names a rule that does not exist."""
    codes = set(available().listed)
    for code in config.ignore:
        if code in codes:
            continue
        close = get_close_matches(
            code,
            sorted(codes),
            n=CLOSE,
            cutoff=ALIKE,
        )
        said = f"; closest: {', '.join(close)}" if close else ""
        yield Complaint(
            said="ignore names what does not exist",
            about=f"{code!r} — no such rule{said}",
        )


def _silent(*, config: Config) -> Iterator[Complaint]:
    """A rule that has a section with nothing to say.

    Zero violations in that case look like a convention kept, and mean a rule
    that checked nothing. An empty section is no trouble on its own: half the
    rules have working defaults, and `[raw-sql]` without a single line forbids
    exactly what it was written for.
    """
    named = prefix(source=config.origin)
    for code, check in sorted(available().listed.items()):
        section = section_of(check=check)
        if not config.enabled(code=code) or section not in config.checks:
            continue
        found = _mute(
            config=config,
            code=code,
            check=check,
            named=named,
        )
        if found is not None:
            yield found


def _mute(
    *,
    config: Config,
    code: str,
    check: Check,
    named: str,
) -> Complaint | None:
    """How exactly this section says nothing; `None` — it does say something."""
    section = section_of(check=check)
    said = "rule is on but silent"
    try:
        settings = config.settings_for(
            code=section,
            model=check.Settings,
        )
    except ConfigError as error:
        return Complaint(
            said="section cannot be read",
            about=f"[{named}{section}] — {_first(said=str(error))}",
        )
    zones = getattr(settings, ZONES, None)
    if zones is not None and not zones:
        return Complaint(
            said=said,
            about=f"[{named}{code}] — no zones named: nowhere to judge",
        )
    if config.checks[section] or not _bare(model=check.Settings):
        return None
    return Complaint(
        said=said,
        about=f"[{named}{section}] — the section is empty and the rule has no defaults",
    )


def _first(*, said: str) -> str:
    """The gist of pydantic's complaint: the field and the reason, no count or link.

    pydantic writes a heading, then the field, then the reason with the type
    and the input value. The reader needs the second and the third, and those
    as one short line.
    """
    lines = [one.strip() for one in said.splitlines()[1:] if one.strip()]
    return ": ".join(one.split(" [type=")[0] for one in lines[:REASON])


def _bare(*, model: type[CheckSettings]) -> bool:
    """Whether the rule has nothing at all without its table.

    `module-length` defaults to a limit in lines, and an empty section means
    "work as the library says". `model-columns` has empty defaults: there an
    empty section means "check nothing".
    """
    return all(
        _nothing(value=field.get_default(call_default_factory=True))
        for field in model.model_fields.values()
    )


def _nothing(*, value: object) -> bool:
    return value is None or value == "" or (isinstance(value, Sized) and not len(value))


def _nowhere(*, config: Config) -> Iterator[Complaint]:
    """An address that nothing on disk answers to.

    A directory was renamed, the layout block stayed — and the rule looks where
    nothing has been for a long time, and stays silent about it.
    """
    places = _places(src=config.src)
    if not places:
        return
    named = prefix(source=config.origin)
    for section, address in sorted(_addressed(config=config)):
        if any(
            depth(
                parts=parts,
                path=address,
            )
            is not None
            for parts in places
        ):
            continue
        yield Complaint(
            said="address that is not on disk",
            about=f"[{named}{section}] — {address!r} not found in {config.src}",
        )


def _addressed(*, config: Config) -> Iterator[tuple[str, str]]:
    """The addresses written in the settings: shared table blocks and zone lists.

    Only these two: the other keys are names of packages, types, constructs,
    and they cannot be told from a path without knowing the rule. A zone inside
    an array of tables (`[[confined-calls.rules]]`) is the same zone, hence the
    step inside.
    """
    shared = _shared()
    for section, table in config.checks.items():
        if section in OWNED:
            continue
        if section in shared:
            yield from ((section, key) for key, value in table.items() if isinstance(value, dict))
        for value in [table, *(one for one in table.values() if isinstance(one, list))]:
            yield from ((section, one) for one in _zones(value=value))


def _zones(*, value: TomlValue) -> Iterator[str]:
    """The zones of a table — or the zones of each table in an array."""
    tables = value if isinstance(value, list) else [value]
    for table in tables:
        if not isinstance(table, dict):
            continue
        named = table.get(ZONES)
        if isinstance(named, list):
            yield from (one for one in named if isinstance(one, str))


def _shared() -> set[str]:
    """The sections a rule reads under something other than its code: a shared table."""
    return {
        section_of(check=check)
        for check in available().listed.values()
        if section_of(check=check) != check.code
    }


def _places(*, src: Path) -> list[tuple[str, ...]]:
    """The path parts of every directory and every module under the source root.

    Modules count the same as directories: `exceptions` is both a directory and
    `exceptions.py`, and to the refusal vocabulary it is one and the same place.
    """
    if not src.is_dir():
        return []
    found = [
        path.relative_to(src).with_suffix("").parts
        for path in src.rglob("*")
        if path.is_dir() or path.suffix == SUFFIX
    ]
    # The first part is the root package, and addresses are written inwards from it.
    return [parts[1:] for parts in found if len(parts) > 1]


def register(*, app: typer.Typer) -> None:
    app.command("doctor")(doctor)
