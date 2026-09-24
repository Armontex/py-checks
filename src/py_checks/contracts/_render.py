"""Building the import-linter contracts file."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from py_checks.config import prefix
from py_checks.contracts._constants import MIGRATIONS, MODULES, SECTION, VERSIONS
from py_checks.contracts._layout import expressions, migrations, modules, package
from py_checks.contracts._settings import contracts

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from pathlib import Path

    from py_checks.config import Config

HEADER: Final = """\
# Import contracts. `py-checks sync` builds this file from the layers that
# exist on disk and from the [{section}] section — there is nothing to edit
# here, the next sync overwrites it. Change the section instead.
"""


def render(
    *,
    root: Path,
    config: Config,
) -> str | None:
    """The contracts file; `None` if there is nothing to check.

    Nothing means either a project that declared no layer at all, or a layout
    in which none of the declared layers is on disk.
    """
    name = package(
        root=root,
        src=config.src,
    )
    if name is None:
        return None
    blocks = _contracts(
        root=root,
        config=config,
        package=name,
    )
    if not blocks:
        return None
    head = contracts(config=config).header.strip() or HEADER.format(
        # The section is named differently in the manifest and in its own
        # settings file: writing one name would send the reader to the wrong
        # place in half the projects.
        section=f"{prefix(source=config.origin)}{SECTION}"
    )
    return "\n".join(
        [
            f"{head.rstrip()}\n",
            _roots(
                root=root,
                package=name,
            ),
            *blocks,
        ]
    )


def _roots(
    *,
    root: Path,
    package: str,
) -> str:
    packages = [package, MIGRATIONS] if migrations(root=root) else [package]
    return _block(
        head="[importlinter]",
        scalars={},
        lists={"root_packages": packages},
    )


def _contracts(
    *,
    root: Path,
    config: Config,
    package: str,
) -> list[str]:
    declared = contracts(config=config)
    table = declared.layers
    known = frozenset(table) | frozenset(declared.composition_root)
    blocks = [
        block
        for layer in sorted(table)
        if (
            block := _layer(
                root=root,
                config=config,
                package=package,
                layer=layer,
                forbidden=known - frozenset(table[layer]),
            )
        )
    ]
    blocks.extend(
        _independence(
            root=root,
            config=config,
            package=package,
        )
    )
    blocks.extend(
        _migrations(
            root=root,
            package=package,
        )
    )
    return blocks


def _layer(
    *,
    root: Path,
    config: Config,
    package: str,
    layer: str,
    forbidden: Iterable[str],
) -> str | None:
    """The contract "this layer may not import that"."""
    sources = expressions(
        root=root,
        src=config.src,
        package=package,
        layer=layer,
    )
    targets = [
        expression
        for other in sorted(forbidden)
        for expression in expressions(
            root=root,
            src=config.src,
            package=package,
            layer=other,
        )
    ]
    if not sources or not targets:
        return None
    return _block(
        head=f"[importlinter:contract:layer-{layer}]",
        scalars={
            "name": f"{layer} imports only what it may",
            "type": "forbidden",
            # Direct imports only. There is no indirect chain to check here:
            # `presentation` calls `application`, and `application` knows
            # `domain` — by the table that is exactly the intended work, and
            # forbidding indirect links would forbid it too.
            "allow_indirect_imports": "True",
        },
        lists={"source_modules": list(sources), "forbidden_modules": targets},
    )


def _independence(
    *,
    root: Path,
    config: Config,
    package: str,
) -> list[str]:
    """Modules do not know each other: a neighbour is called via a port, not by name."""
    if not modules(
        root=root,
        src=config.src,
        package=package,
    ):
        return []
    return [
        _block(
            head="[importlinter:contract:modules]",
            scalars={"name": "modules are independent", "type": "independence"},
            lists={"modules": [f"{package}.{MODULES}.*"]},
        ),
    ]


def _migrations(
    *,
    root: Path,
    package: str,
) -> list[str]:
    """A migration describes the schema without calling the app: code moves on, schema stays.

    Only `versions` is looked at: `env.py` is not the history but what runs
    it, and importing the model metadata is part of its job.
    """
    if not migrations(root=root):
        return []
    return [
        _block(
            head=f"[importlinter:contract:{MIGRATIONS}]",
            scalars={"name": "migrations do not know the application", "type": "forbidden"},
            lists={
                "source_modules": [f"{MIGRATIONS}.{VERSIONS}"],
                "forbidden_modules": [package],
            },
        ),
    ]


def _block(
    *,
    head: str,
    scalars: Mapping[str, str],
    lists: Mapping[str, Sequence[str]],
) -> str:
    """One ini section.

    Lists are written one value per line, even a single value: import-linter
    reads a list field written on one line character by character — and looks
    for a package `p`.
    """
    lines = [head, *(f"{key} = {value}" for key, value in scalars.items())]
    for key, values in lists.items():
        lines.append(f"{key} =")
        lines.extend(f"    {value}" for value in values)
    return "\n".join(lines) + "\n"
