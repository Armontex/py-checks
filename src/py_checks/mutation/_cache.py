"""What mutmut keeps in `mutants/` between runs, read before it runs again."""

from __future__ import annotations

import ast
import hashlib
from pathlib import PurePosixPath
from typing import TYPE_CHECKING, Final

from pydantic import BaseModel, Field, ValidationError

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from pathlib import Path

MUTANTS: Final = "mutants"
STATS: Final = "mutmut-stats.json"

# What the cached verdicts rested on when they were last reached. The gate's
# own file, kept in `mutants/` so that deleting the cache deletes it too.
VERDICTS: Final = "py-checks-verdicts.json"
Digests = dict[str, dict[str, str]]

MUTANTS_OF: Final = "{module}.{function}__mutmut_*"
# mutmut picks the tests of its clean run by exact names only: a pattern
# matches no entry of its map, and without one it runs the whole suite. Every
# function with mutants has a first one.
FIRST_MUTANT: Final = "{module}.{function}__mutmut_1"
# A test's id starts with its file: `tests/test_totals.py::test_total[1]`.
TEST_FILE: Final = "::"

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


class Stats(BaseModel):
    """The part of `mutmut-stats.json` the gate reads: which tests reach a
    function, and every test mutmut has collected."""

    tests_by_mangled_function_name: dict[str, list[str]] = Field(default_factory=dict)
    duration_by_test: dict[str, float] = Field(default_factory=dict)


class Remembered(BaseModel):
    """`functions` — one hash per function, by module: its source and its tests.
    `suite` — one hash of every test file: a survivor is owed a new verdict by
    any new test, not only by those that reached it before."""

    suite: str = ""
    functions: Digests = Field(default_factory=dict)


def collected(*, root: Path) -> bool:
    """Whether mutmut has a test map: without one a run collects it in full."""
    return (root / MUTANTS / STATS).is_file()


def digests(
    *,
    root: Path,
    files: Mapping[str, PurePosixPath],
) -> Digests:
    """What each function's verdict rests on, as one hash per function.

    Its own source; the module's code outside functions, which it may read;
    the tests mutmut's map says reach it, by id and by the content of their
    files. A verdict whose hash is unchanged was reached against the same code
    and the same tests, and running it again would only repeat it.
    """
    # ponytail: a test is seen through its own file; a changed conftest or helper
    # module is not, and `--rerun` is the way past that.
    tests = _stats(root=root).tests_by_mangled_function_name
    read: dict[str, str] = {}
    found: Digests = {}
    for module, path in files.items():
        defined, context = _definitions(path=root / path)
        found[module] = {}
        for name, source in defined.items():
            covering = sorted(tests.get(f"{module}.{name}", ()))
            words = [context, source, *covering]
            words += (
                _content(
                    root=root,
                    test=test,
                    read=read,
                )
                for test in covering
            )
            found[module][name] = hashlib.sha256("\0".join(words).encode()).hexdigest()
    return found


def outdated(
    *,
    now: Digests,
    before: Digests,
) -> tuple[str, ...]:
    """Mutants whose verdict no longer stands: of a function that changed, whose
    tests changed, that is new or that is gone — the last to drop its verdicts."""
    names: list[str] = []
    for module, functions in now.items():
        known = before.get(module, {})
        moved = {name for name, digest in functions.items() if known.get(name) != digest}
        names += (
            shape.format(
                module=module,
                function=name,
            )
            for name in sorted(moved | (known.keys() - functions.keys()))
            for shape in (MUTANTS_OF, FIRST_MUTANT)
        )
    return tuple(names)


def suite(*, root: Path) -> str:
    """One hash of every Python file in the directories mutmut's tests live in.

    A new test — in a new file or an old one — lands in the map only after a
    run collects it, and a mutant that survived may die by it.
    """
    tests = _stats(root=root).duration_by_test
    homes = sorted({PurePosixPath(test.partition(TEST_FILE)[0]).parts[0] for test in tests})
    files = sorted(path for home in homes for path in (root / home).rglob("*.py"))
    words = (f"{path.relative_to(root)}\0{path.read_bytes().hex()}" for path in files)
    return hashlib.sha256("\0".join(words).encode()).hexdigest() if files else ""


def remembered(*, root: Path) -> Remembered:
    """What the last verdicts rested on; an unreadable file stands for nothing known."""
    try:
        return Remembered.model_validate_json((root / MUTANTS / VERDICTS).read_bytes())
    except OSError, ValidationError:
        return Remembered()


def remember(
    *,
    root: Path,
    found: Digests,
    tests: str,
) -> None:
    path = root / MUTANTS / VERDICTS
    path.parent.mkdir(exist_ok=True)
    known = remembered(root=root).functions | found
    path.write_text(
        Remembered(
            suite=tests,
            functions=known,
        ).model_dump_json(),
        encoding="utf-8",
    )


def functions(*, path: Path) -> set[str]:
    """The functions and methods of a file, named the way mutmut names them."""
    return set(_definitions(path=path)[0])


def _definitions(*, path: Path) -> tuple[dict[str, str], str]:
    """A file's functions and methods by mutmut's name, each with its source, and
    the rest of the file's code.

    Only those at the top and inside classes: mutmut does not mutate a
    function nested in another one. Its own copies — `x_total__mutmut_1` and
    the rest — are not functions of the source and are left out.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except OSError, SyntaxError:
        return {}, ""
    found: dict[str, str] = {}
    rest: list[str] = []
    bodies: list[tuple[list[ast.stmt], str]] = [(tree.body, "")]
    while bodies:
        body, owner = bodies.pop()
        for node in body:
            if isinstance(node, ast.ClassDef):
                bodies.append((node.body, f"{owner}.{node.name}" if owner else node.name))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                name = mangled(
                    owner=owner,
                    name=node.name,
                )
                found[name] = ast.dump(node)
            else:
                rest.append(ast.dump(node))
    return {name: source for name, source in found.items() if MUTANT not in name}, "".join(rest)


def _stats(*, root: Path) -> Stats:
    try:
        return Stats.model_validate_json((root / MUTANTS / STATS).read_bytes())
    except OSError, ValidationError:
        return Stats()


def _content(
    *,
    root: Path,
    test: str,
    read: dict[str, str],
) -> str:
    """The hash of a test's file, each file read once; a file that is gone hashes empty."""
    file = test.partition(TEST_FILE)[0]
    if file not in read:
        path = root / file
        read[file] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
    return read[file]


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
