"""What `--fix` changes: the definitions behind the violations, and those that must follow.

The project is read once, as git lists it, and every later step asks the same
parsed modules.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Protocol

from py_checks.checks.signatures._functions import Definition, definitions, receiver
from py_checks.core import Edit, ParsedFile
from py_checks.translations import TranslationError, tracked

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from py_checks.core import Violation


PYTHON: Final = ".py"


# Where the walk never looks when the project is not a git repository.
SKIPPED: Final[frozenset[str]] = frozenset({"venv", "node_modules", "site-packages"})


class Star(Protocol):
    """The rule's own edit of a signature: a `*` put in, or one moved to the front."""

    def __call__(
        self,
        *,
        definition: Definition,
        file: ParsedFile,
    ) -> Edit | None: ...


@dataclass(frozen=True, slots=True)
class Target:
    """A definition the fix is about to change, and how its calls change with it.

    `names` are the parameters that become named, in order; `kept` is how many
    leading positional arguments a call keeps — those before `/`. A target
    without a violation is a follower: a test double of a port, outside the
    checked sources, that has to change along with the port it imitates.
    """

    violation: Violation | None
    path: Path
    definition: Definition
    names: tuple[str, ...]
    kept: int
    edit: Edit

    @property
    def name(self) -> str:
        return self.definition.node.name

    @property
    def family(self) -> tuple[str, ...]:
        """What changes together: a method with every method of its name and signature.

        A port and its implementations are not linked by inheritance, only by
        shape, and a call through the port resolves to the port. Changing one
        of them alone leaves the other no longer matching it.
        """
        if self.definition.method:
            return (self.name, *self.names)
        return (str(self.path), str(self.definition.node.lineno))


@dataclass(frozen=True, slots=True)
class Module:
    """A project file, parsed once for everything the fix asks of it."""

    path: Path
    text: str
    tree: ast.Module | None


def project_modules(*, root: Path) -> list[Module]:
    """Every Python file of the project, parsed; `tree` is empty where it does not parse."""
    found: list[Module] = []
    for path in _files(root=root):
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            tree = None
        found.append(
            Module(
                path=path.resolve(),
                text=text,
                tree=tree,
            )
        )
    return found


def _files(*, root: Path) -> list[Path]:
    """The project's files as git sees them: `.venv` and `mutants/` are never callers.

    Outside git, a walk that skips hidden directories and installed packages.
    """
    try:
        listed = [root / path for path in tracked(root=root)]
    except TranslationError:
        return [
            path
            for path in root.rglob(f"*{PYTHON}")
            if not any(
                part.startswith(".") or part in SKIPPED
                for part in path.relative_to(root).parts[:-1]
            )
        ]
    return [path for path in listed if path.suffix == PYTHON]


def violated(
    *,
    violations: Sequence[Violation],
    modules: Sequence[Module],
) -> tuple[list[Target], list[Violation]]:
    """The definitions behind the violations; a violation with no edit is left as it is."""
    trees = {module.path: module.tree for module in modules}
    targets: list[Target] = []
    left: list[Violation] = []
    for violation in violations:
        path = violation.path.resolve()
        tree = trees.get(path)
        if tree is None:
            tree = ast.parse(violation.path.read_text(encoding="utf-8"))
        found = next(
            (one for one in definitions(node=tree) if one.node.lineno == violation.line),
            None,
        )
        if violation.edit is None or found is None:
            left.append(violation)
            continue
        names, kept = parameters(definition=found)
        targets.append(
            Target(
                violation=violation,
                path=path,
                definition=found,
                names=names,
                kept=kept,
                edit=violation.edit,
            )
        )
    return targets, left


def following(
    *,
    targets: Sequence[Target],
    modules: Sequence[Module],
    source: Path,
    star: Star,
    root: Path,
) -> tuple[list[Target], dict[tuple[str, ...], str]]:
    """The methods that share a target's name and signature, and must change with it.

    They are the port of an implementation or another implementation of the
    port, and one changed alone stops matching the other. Inside the checked
    sources such a method was left on purpose — a mark, a rule's exception —
    and it stops the family. Outside them it is a test double nobody judged,
    and it follows.
    """
    fixed = {(target.path, target.definition.node.lineno) for target in targets}
    families = {target.family for target in targets if target.definition.method}
    followers: list[Target] = []
    stopped: dict[tuple[str, ...], str] = {}
    for module in modules:
        for definition in definitions(node=module.tree) if module.tree else ():
            if definition.method and (module.path, definition.node.lineno) not in fixed:
                follower = _follower(
                    definition=definition,
                    module=module,
                    checked=module.path.is_relative_to(source.resolve()),
                    families=families,
                    star=star,
                    stopped=stopped,
                    root=root,
                )
                if follower is not None:
                    followers.append(follower)
    return followers, stopped


def _follower(
    *,
    definition: Definition,
    module: Module,
    checked: bool,
    families: set[tuple[str, ...]],
    star: Star,
    stopped: dict[tuple[str, ...], str],
    root: Path,
) -> Target | None:
    """The method as a follower of its family, or the reason it stops the family."""
    names, kept = parameters(definition=definition)
    family = (definition.node.name, *names)
    where = relative(
        path=module.path,
        line=definition.node.lineno,
        root=root,
    )
    if family not in families:
        # A double outside the checked sources is not type-checked as strictly:
        # one that names its parameters its own way still stands in for the
        # real method, and breaks on named arguments.
        for other in families:
            if not checked and other[0] == definition.node.name:
                stopped.setdefault(
                    other, f"{where} has a method of that name with other parameters"
                )
        return None
    edit = star(
        definition=definition,
        file=ParsedFile(
            path=module.path,
            text=module.text,
        ),
    )
    if checked or edit is None:
        stopped.setdefault(family, f"{where} has the same signature and stays")
        return None
    return Target(
        violation=None,
        path=module.path,
        definition=definition,
        names=names,
        kept=kept,
        edit=edit,
    )


def parameters(*, definition: Definition) -> tuple[tuple[str, ...], int]:
    """The parameters that become named, and how many positional ones stay before `/`."""
    arguments = definition.node.args
    skip = receiver(definition=definition)
    named_from = max(skip - len(arguments.posonlyargs), 0)
    return (
        tuple(argument.arg for argument in arguments.args[named_from:]),
        max(len(arguments.posonlyargs) - skip, 0),
    )


def relative(
    *,
    path: Path,
    root: Path,
    line: int | None = None,
) -> str:
    """The path from the project root, and the line when there is one: `src/app/b.py:3`."""
    try:
        shown = path.relative_to(root.resolve()).as_posix()
    except ValueError:
        shown = path.as_posix()
    return shown if line is None else f"{shown}:{line}"
