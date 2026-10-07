"""Who calls a function: what `--fix` must rewrite before a parameter becomes named.

A `*` in a signature turns every positional call into a type error, and the
calls live in other modules, in tests, behind an import alias. The rule finds
them in two steps. A plain walk over the tree collects every place the name
is written — cheap and complete, but blind to whose name it is. jedi then
says, for each place, whose it is: ours, someone else's (`dict.get`), or
nobody knows. "Nobody knows" stops the fix: a call that cannot be told apart
is a call that could be broken, and a fix that cannot repair every caller is
not applied at all.
"""

from __future__ import annotations

import ast
import os
import subprocess
from collections import defaultdict
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Final, Protocol, cast

import jedi  # pyright: ignore[reportMissingTypeStubs] - jedi ships no stubs; `Found` types what is read

from py_checks.checks._names import names as named
from py_checks.checks.signatures._functions import receiver
from py_checks.checks.signatures._stops import stops
from py_checks.checks.signatures._targets import following, project_modules, relative, violated
from py_checks.core import Edit, Patch, Repair, column

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence

    from py_checks.checks.signatures._targets import Module, Star, Target
    from py_checks.core import Violation


VENV: Final = ".venv"


VIRTUAL_ENV: Final = "VIRTUAL_ENV"

# Only what is committed: an untracked `.venv` without a `.gitignore` is still
# one's own, made on this machine.
COMMITTED: Final = ("git", "ls-files", "--cached", "--")


CLASSMETHOD: Final = "classmethod"


class Found(Protocol):
    """What the fix reads of a jedi definition: the file and the line it is in."""

    @property
    def module_path(self) -> Path | None: ...

    @property
    def line(self) -> int | None: ...


@dataclass(frozen=True, slots=True)
class Site:
    """A place a target's name is written: a call or a mention."""

    path: Path
    node: ast.Name | ast.Attribute
    call: ast.Call | None
    name: str


def callers(
    *,
    violations: Sequence[Violation],
    root: Path,
    source: Path,
    star: Star,
) -> Repair:
    """The fix for every violation whose callers can all be found, and the rest left."""
    modules = project_modules(root=root)
    fixed, left = violated(
        violations=violations,
        modules=modules,
    )
    followers, unmatched = following(
        targets=fixed,
        modules=modules,
        source=source,
        star=star,
        root=root,
    )
    targets = [*fixed, *followers]
    # The definition's own reason first: "called through its class" says more
    # about a constructor than any double of the same name does.
    stopped = stops(
        targets=targets,
        modules=modules,
        root=root,
    )
    for family, reason in unmatched.items():
        stopped.setdefault(family, reason)
    edits = _calls(
        targets=targets,
        modules=modules,
        project=_project(
            root=root,
            source=source,
        ),
        stopped=stopped,
        root=root,
    )
    return _repair(
        targets=targets,
        edits=edits,
        stopped=stopped,
        left=left,
    )


def _repair(
    *,
    targets: Sequence[Target],
    edits: dict[tuple[str, ...], list[Patch]],
    stopped: dict[tuple[str, ...], str],
    left: list[Violation],
) -> Repair:
    """One patch set per family, shared by its members: they stand or fall together."""
    members: dict[tuple[str, ...], list[Target]] = defaultdict(list)
    for target in targets:
        members[target.family].append(target)
    repair = Repair(
        patches={},
        left=list(left),
    )
    for family, group in members.items():
        violated = [target.violation for target in group if target.violation is not None]
        if family in stopped:
            repair.left.extend(
                replace(
                    violation,
                    message=f"{violation.message}; not fixed: {stopped[family]}",
                )
                for violation in violated
            )
            continue
        shared = (
            *(
                Patch(
                    path=target.path,
                    edit=target.edit,
                )
                for target in group
            ),
            *edits.get(family, ()),
        )
        repair.patches.update((violation, shared) for violation in violated)
    return repair


def _project(
    *,
    root: Path,
    source: Path,
) -> jedi.Project:
    """jedi over the project, in the project's own environment when there is one.

    A hook runs in an environment of its own, where neither the project nor
    its libraries are installed: without the project's `.venv` a library call
    resolves to nothing and stops the fix of every function sharing its name.
    """
    environment = _environment(root=root)
    return jedi.Project(
        path=root,
        environment_path=environment,
        added_sys_path=(str(source),),
    )


def _environment(*, root: Path) -> str | None:
    """The interpreter jedi starts: the project's `.venv`, when git vouches for it.

    jedi runs that interpreter to learn its paths, so the fix runs whatever
    lies at `.venv/bin/python`. A `.venv` of one's own is not in git's index;
    one that came with the repository — or with an archive git cannot speak
    for — is someone else's program, and the fix stays in its own environment:
    fewer calls resolved, nothing run.
    """
    venv = root / VENV
    if venv.is_dir() and _local(root=root):
        return str(venv)
    return os.environ.get(VIRTUAL_ENV) or None


def _local(*, root: Path) -> bool:
    """Whether git confirms nothing under `.venv` is committed; no answer is a no."""
    try:
        listed = subprocess.run(  # noqa: S603 — a fixed list of arguments, no shell
            [*COMMITTED, VENV],
            cwd=root,
            capture_output=True,
            check=True,
        )
    except OSError, subprocess.CalledProcessError:
        return False
    return not listed.stdout.strip()


def _calls(
    *,
    targets: Sequence[Target],
    modules: Sequence[Module],
    project: jedi.Project,
    stopped: dict[tuple[str, ...], str],
    root: Path,
) -> dict[tuple[str, ...], list[Patch]]:
    """The call edits of every family; a family that meets a doubtful place is stopped."""
    index = {(target.path, target.definition.node.lineno): target for target in targets}
    # A stopped family needs no more reasons: its places are not worth a lookup.
    wanted = {target.name for target in targets if target.family not in stopped}
    edits: dict[tuple[str, ...], list[Patch]] = defaultdict(list)
    for module in modules:
        sites = list(
            _sites(
                module=module,
                wanted=wanted,
            )
        )
        if not sites:
            continue
        script = jedi.Script(
            code=module.text,
            path=module.path,
            project=project,
        )
        lines = module.text.splitlines()
        for site in sites:
            _place(
                site=site,
                found=_resolved(
                    site=site,
                    script=script,
                    lines=lines,
                    index=index,
                ),
                lines=lines,
                targets=targets,
                edits=edits,
                stopped=stopped,
                where=relative(
                    path=site.path,
                    line=site.node.lineno,
                    root=root,
                ),
            )
    return edits


def _resolved(
    *,
    site: Site,
    script: jedi.Script,
    lines: Sequence[str],
    index: dict[tuple[Path, int], Target],
) -> list[Target] | None:
    """The targets this place names; `None` when nobody knows whose name it is.

    An empty list is someone else's name: `dict.get`, a library, a function of
    the project the fix does not change. A place that names a target and
    something else at once — a union type — is as good as unknown.
    """
    line, offset = _point(node=site.node)
    found = _goto(
        script=script,
        line=line,
        column=column(
            line=lines[line - 1],
            offset=offset,
        )
        - 1,
    )
    if not found:
        return None
    hits = [
        index.get((Path(one.module_path).resolve(), one.line))
        for one in found
        if one.module_path is not None and one.line is not None
    ]
    mine = [hit for hit in hits if hit is not None]
    if mine and len(mine) < len(found):
        return None
    return mine


def _goto(
    *,
    script: jedi.Script,
    line: int,
    column: int,
) -> list[Found]:
    """Where jedi says the name at this point is defined; jedi ships no type hints."""
    found = script.goto(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        line,
        column,
        follow_imports=True,
    )
    return cast("list[Found]", found)


def _place(
    *,
    site: Site,
    found: list[Target] | None,
    lines: Sequence[str],
    targets: Sequence[Target],
    edits: dict[tuple[str, ...], list[Patch]],
    stopped: dict[tuple[str, ...], str],
    where: str,
) -> None:
    """Record what one place means for the families its name could belong to."""
    if found is None:
        for target in targets:
            if target.name == site.name:
                stopped.setdefault(target.family, f"{where} cannot be resolved")
        return
    for target in found:
        reason, made = _rewritten(
            site=site,
            target=target,
            lines=lines,
        )
        if reason is not None:
            stopped.setdefault(target.family, f"{where} {reason}")
        else:
            edits[target.family].extend(made)


def _rewritten(
    *,
    site: Site,
    target: Target,
    lines: Sequence[str],
) -> tuple[str | None, list[Patch]]:
    """The call with its positional arguments named, or why it cannot be."""
    call = site.call
    if call is None:
        return "passes it as a value", []
    if any(isinstance(argument, ast.Starred) for argument in call.args):
        return "unpacks arguments into it", []
    if _through_class(
        site=site,
        target=target,
    ):
        return "calls it through the class, receiver included", []
    moved = call.args[target.kept :]
    if len(moved) > len(target.names):
        return "passes more arguments than it takes", []
    return None, [
        Patch(
            path=site.path,
            edit=Edit(
                line=argument.lineno,
                column=(
                    at := column(
                        line=lines[argument.lineno - 1],
                        offset=argument.col_offset,
                    )
                ),
                end_line=argument.lineno,
                end_column=at,
                text=f"{parameter}=",
            ),
        )
        for argument, parameter in zip(moved, target.names, strict=False)
    ]


def _through_class(
    *,
    site: Site,
    target: Target,
) -> bool:
    """`Repo.get(repo, key)`: the receiver is the first positional argument."""
    if not isinstance(site.node, ast.Attribute) or not isinstance(site.node.value, ast.Name):
        return False
    plain = target.definition.method and receiver(definition=target.definition) == 1
    if not plain or CLASSMETHOD in set(named(nodes=target.definition.node.decorator_list)):
        return False
    return site.node.value.id[:1].isupper()


def _sites(
    *,
    module: Module,
    wanted: set[str],
) -> Iterator[Site]:
    """Every place in the module where one of the wanted names is written.

    `from orders import price as quote` makes `quote` a place of `price`.
    """
    if module.tree is None:
        return
    aliases = dict(
        _aliases(
            tree=module.tree,
            wanted=wanted,
        )
    )
    callees = {id(node.func): node for node in ast.walk(module.tree) if isinstance(node, ast.Call)}
    for node in ast.walk(module.tree):
        match node:
            case ast.Name(id=name) if name in wanted or name in aliases:
                spelled = aliases.get(name, name)
            case ast.Attribute(attr=name) if name in wanted:
                spelled = name
            case _:
                continue
        yield Site(
            path=module.path,
            node=node,
            call=callees.get(id(node)),
            name=spelled,
        )


def _aliases(
    *,
    tree: ast.Module,
    wanted: set[str],
) -> Iterable[tuple[str, str]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.asname and alias.name in wanted:
                    yield alias.asname, alias.name


def _point(*, node: ast.Name | ast.Attribute) -> tuple[int, int]:
    """Where the name itself starts: for `repo.get`, the `get`, not the `repo`."""
    if isinstance(node, ast.Name):
        return node.lineno, node.col_offset
    end_line = node.end_lineno or node.lineno
    end = node.end_col_offset or 0
    return end_line, end - len(node.attr.encode("utf-8"))
