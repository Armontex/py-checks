"""What mutmut keeps in `mutants/` between runs, read before it runs again."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path, PurePosixPath

MUTANTS: Final = "mutants"
STATS: Final = "mutmut-stats.json"

# How mutmut names a function: `x_total` for a function, `xǁOrderǁtotal` for a
# method; the mutants of `x_total` are `x_total__mutmut_1` and on.
FUNCTION: Final = "x_{name}"
METHOD: Final = "xǁ{owner}ǁ{name}"
MUTANT: Final = "__mutmut"


def stale(
    *,
    root: Path,
    paths: Iterable[PurePosixPath],
) -> int:
    """How many functions of the changed files mutmut's test map has never seen.

    mutmut collects the map of which test reaches which function again only
    for tests it has never seen. A test that already existed and now reaches a
    function a refactor extracted is never added to that function's entry, and
    every mutant of it survives. The copy in `mutants/` is the source as of
    the run that last updated the map: a function it lacks is one the map
    cannot know. No map at all — nothing is stale, mutmut collects it in full.
    """
    if not (root / MUTANTS / STATS).is_file():
        return 0
    return sum(
        len(functions(path=root / path) - functions(path=root / MUTANTS / path)) for path in paths
    )


def forget(*, root: Path) -> None:
    """Drop the test map: the next run collects it from scratch."""
    (root / MUTANTS / STATS).unlink(missing_ok=True)


def functions(*, path: Path) -> set[str]:
    """The functions and methods of a file, named the way mutmut names them.

    Only those at the top and inside classes: mutmut does not mutate a
    function nested in another one. Its own copies — `x_total__mutmut_1` and
    the rest — are not functions of the source and are left out.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except OSError, SyntaxError:
        return set()
    found: set[str] = set()
    bodies: list[tuple[list[ast.stmt], str]] = [(tree.body, "")]
    while bodies:
        body, owner = bodies.pop()
        for node in body:
            if isinstance(node, ast.ClassDef):
                bodies.append((node.body, f"{owner}.{node.name}" if owner else node.name))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                found.add(
                    mangled(
                        owner=owner,
                        name=node.name,
                    )
                )
    return {name for name in found if MUTANT not in name}


def mangled(
    *,
    owner: str,
    name: str,
) -> str:
    if owner:
        return METHOD.format(
            owner=owner,
            name=name,
        )
    return FUNCTION.format(name=name)
