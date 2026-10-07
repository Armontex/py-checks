"""Why a family is not fixed before any call is looked at: who calls it is not in the code.

A constructor reached through its class, a decorator that calls the function
itself, a base from a library, a name handed to `patch` as a string, a method
swapped by assignment — each is a caller the walk over the tree cannot see.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, Final

from py_checks.checks._names import name
from py_checks.checks._names import names as named
from py_checks.checks.signatures._targets import relative

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence
    from pathlib import Path

    from py_checks.checks.signatures._targets import Module, Target


# Called through the class or the instance, not by their own name: `Repo(x)`
# reaches `__init__`, and so does `SubRepo(x)` of a subclass that has none.
# Tracing that is a job of its own; until then the fix leaves them be.
CONSTRUCTORS: Final[frozenset[str]] = frozenset({"__init__", "__new__", "__call__"})


# Decorators that leave the call as the caller wrote it. Any other one may
# call the function itself — `@app.get`, `@pytest.fixture`, `@singledispatch` —
# and how it calls it is not written anywhere in the project.
TRANSPARENT: Final[frozenset[str]] = frozenset(
    {"staticmethod", "classmethod", "abstractmethod", "override"},
)


# Bases that call none of a subclass's methods by position. Any other base
# from outside the project might: `ast.NodeVisitor` calls `visit_Name(node)`.
NEUTRAL: Final[frozenset[str]] = frozenset(
    {"object", "Protocol", "ABC", "Generic", "Exception", "BaseException"},
)


# Calls that take a name as a string: `monkeypatch.setattr(module, "price", fake)`
# replaces the function with a double whose signature the fix cannot see, and
# `patch("orders.price")` the same. `object` is `patch.object`.
PATCHERS: Final[frozenset[str]] = frozenset(
    {"setattr", "getattr", "delattr", "hasattr", "patch", "object"},
)


def stops(
    *,
    targets: Sequence[Target],
    modules: Sequence[Module],
    root: Path,
) -> dict[tuple[str, ...], str]:
    """The families stopped before any call is looked at, and why."""
    foreign = _foreign(modules=modules)
    stopped: dict[tuple[str, ...], str] = {}
    for target in targets:
        reason = _shape(
            target=target,
            foreign=foreign,
        )
        if reason is not None:
            stopped.setdefault(target.family, reason)
    for module in modules:
        where = relative(
            path=module.path,
            root=root,
        )
        if module.tree is None:
            for target in targets:
                if target.name in module.text:
                    stopped.setdefault(target.family, f"{where} does not parse")
            continue
        for line, replaced in _replaced(tree=module.tree):
            for target in targets:
                if replaced == target.name:
                    stopped.setdefault(target.family, f"{where}:{line} replaces it")
        for line, spelled in _strings(tree=module.tree):
            for target in targets:
                if spelled == target.name or spelled.endswith(f".{target.name}"):
                    stopped.setdefault(
                        target.family,
                        f"{where}:{line} names it in a string, which --fix cannot follow",
                    )
    return stopped


def _replaced(*, tree: ast.Module) -> Iterator[tuple[int, str]]:
    """`service.prepare = fake`: a method swapped for a function of any signature."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            yield node.lineno, node.attr


def _strings(*, tree: ast.Module) -> Iterator[tuple[int, str]]:
    """The names handed to a patch or a lookup as strings."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and name(node=node.func) in PATCHERS:
            for argument in node.args:
                if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                    yield argument.lineno, argument.value


def _shape(
    *,
    target: Target,
    foreign: dict[str, str],
) -> str | None:
    """Why the definition itself rules the fix out: who calls it is not in the project."""
    if target.name in CONSTRUCTORS:
        return f"{target.name} is called through its class, which --fix does not trace"
    for decorator in named(nodes=target.definition.node.decorator_list):
        if decorator not in TRANSPARENT:
            return f"decorated with @{decorator}, which decides how it is called"
    if target.definition.method:
        owner = target.definition.name.rsplit(".", maxsplit=2)[-2]
        if owner in foreign:
            return f"{owner} derives from {foreign[owner]}, which may call it by position"
    return None


def _foreign(*, modules: Sequence[Module]) -> dict[str, str]:
    """The project's classes that descend from a base outside it, and that base.

    Classes are known by name only: two classes of one name in two modules
    are one class here. The cost is a fix not applied, never a wrong one.
    """
    bases: dict[str, list[str]] = {}
    for module in modules:
        if module.tree is None:
            continue
        for node in ast.walk(module.tree):
            if isinstance(node, ast.ClassDef):
                bases.setdefault(node.name, []).extend(named(nodes=node.bases))
    found: dict[str, str] = {}
    for owner in bases:
        root = _outside(
            name=owner,
            bases=bases,
            seen=set(),
        )
        if root is not None:
            found[owner] = root
    return found


def _outside(
    *,
    name: str,
    bases: dict[str, list[str]],
    seen: set[str],
) -> str | None:
    """The first base outside the project this class descends from."""
    seen.add(name)
    for base in bases.get(name, ()):
        if base in NEUTRAL or base in seen:
            continue
        if base not in bases:
            return base
        if (
            found := _outside(
                name=base,
                bases=bases,
                seen=seen,
            )
        ) is not None:
            return found
    return None
