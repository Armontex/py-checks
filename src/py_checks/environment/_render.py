"""Building `.env.example` from the project's settings classes."""

from __future__ import annotations

import enum
import importlib
import json
import sys
from pathlib import Path
from textwrap import wrap
from typing import TYPE_CHECKING, Any, Final

from pydantic import BaseModel, SecretStr
from pydantic_core import PydanticUndefined

from py_checks.config import ConfigError, prefix
from py_checks.environment._constants import SECTION
from py_checks.environment._settings import example

if TYPE_CHECKING:
    from pydantic.fields import FieldInfo

    from py_checks.config import Config

HEADER: Final = """\
# Environment variables the service reads. `py-checks sync` builds this file
# from the settings classes listed in [{section}] — there is nothing to edit
# here, the next sync overwrites it. A default is here so that it can be seen,
# not because the variable has to be set.
"""

SEPARATOR: Final = ":"

# Comment width: the same that the docstrings themselves are wrapped to.
WIDTH: Final = 77


def render(
    *,
    root: Path,
    config: Config,
) -> tuple[Path, str] | None:
    """The file's path and text; `None` if the project declared no class."""
    declared = example(config=config)
    if not declared.settings:
        return None
    blocks = [
        block
        for name in declared.settings
        for block in _blocks(
            model=_imported(
                path=name,
                root=root,
                src=config.src,
            ),
            seen=set(),
        )
    ]
    head = declared.header.strip() or HEADER.format(
        section=f"{prefix(source=config.origin)}{SECTION}"
    )
    return root / declared.path, "\n".join(
        [
            f"{head.rstrip()}\n",
            *blocks,
        ]
    )


def _imported(
    *,
    path: str,
    root: Path,
    src: Path,
) -> type[BaseModel]:
    """A settings class from a `module:Class` record.

    An import rather than reading the source: the variable's name is the value
    of a field attribute, and it is assembled by a call (`AliasChoices(...)`, a
    name computed when the class is created). Reading it as text would mean
    performing that call yourself.
    """
    module, _, attribute = path.partition(SEPARATOR)
    if not attribute:
        message = f"[{SECTION}]: {path!r} — expected a record of the form `module:Class`"
        raise ConfigError(message)
    _reachable(
        root=root,
        src=src,
    )
    try:
        found = getattr(importlib.import_module(module), attribute)
    except (ImportError, AttributeError) as error:
        raise ConfigError(f"[{SECTION}]: {path!r} cannot be imported: {error}") from error
    if not (isinstance(found, type) and issubclass(found, BaseModel)):
        message = f"[{SECTION}]: {path!r} — not a pydantic model"
        raise ConfigError(message)
    return found


def _reachable(
    *,
    root: Path,
    src: Path,
) -> None:
    """Let the import find the project's package even if the project is not installed."""
    for directory in (root / src, root):
        name = str(directory)
        if directory.is_dir() and name not in sys.path:
            sys.path.insert(0, name)


def _blocks(
    *,
    model: type[BaseModel],
    seen: set[type[BaseModel]],
) -> list[str]:
    """A class and the sections nested in it, each as a block of its own.

    Naming the root class is enough for a project: it has already listed the
    sections — in its own fields — and repeating that list in the settings
    would start a second one that drifts from the first.
    """
    if model in seen:
        return []
    seen.add(model)
    lines = [f"# --- {_origin(model=model)} ---", *_commented(text=_said(model=model))]
    nested: list[str] = []
    for field in model.model_fields.values():
        section = _section(field=field)
        if section is not None:
            nested.extend(
                _blocks(
                    model=section,
                    seen=seen,
                )
            )
            continue
        name = _variable(field=field)
        if name is None:
            continue
        lines.extend(_commented(text=field.description))
        lines.append(f"{name}={_value(field=field)}")
    # A root with no variables of its own stays out of the file: a heading with
    # a docstring and nothing under it says nothing.
    own = [] if len(lines) == 1 or not _variables(lines=lines) else ["\n".join(lines) + "\n"]
    return own + nested


def _variables(*, lines: list[str]) -> bool:
    """Whether the block has at least one variable rather than only comments."""
    return any(not line.startswith("#") for line in lines)


def _origin(*, model: type[BaseModel]) -> str:
    """How the class is written in the settings: `module:Class`."""
    return f"{model.__module__}{SEPARATOR}{model.__qualname__}"


def _section(*, field: FieldInfo) -> type[BaseModel] | None:
    """The nested settings section, if the field is one.

    A section is recognised by the field's type: an ordinary value can have a
    `default_factory` too, while a model in the annotation means exactly
    "another group of variables starts here".
    """
    annotation = field.annotation
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    return None


def _said(*, model: type[BaseModel]) -> str | None:
    """The first paragraph of the class docstring: what this section is for.

    A paragraph, not a line: a docstring is wrapped to the file's width, and
    its first line breaks off in the middle of a sentence.
    """
    if model.__doc__ is None:
        return None
    paragraph = model.__doc__.strip().split("\n\n", maxsplit=1)[0]
    return " ".join(paragraph.split()) or None


def _commented(*, text: str | None) -> list[str]:
    """Text as a comment, wrapped to the line width."""
    if not text:
        return []
    return [f"# {line}" for line in wrap(text, width=WIDTH)]


def _variable(*, field: FieldInfo) -> str | None:
    """The name of the variable the field reads; `None` if the field is not one.

    A field built by a factory is a nested section: the variables are read by
    its own fields, and it has none itself.
    """
    if field.default_factory is not None:
        return None
    alias = field.validation_alias
    if isinstance(alias, str):
        return alias
    choices = getattr(alias, "choices", ())
    named = [choice for choice in choices if isinstance(choice, str)]
    return named[0] if named else None


def _value(*, field: FieldInfo) -> str:
    """The default, written the way an environment file writes it."""
    default = field.default
    if default is PydanticUndefined or default is None:
        return ""
    return _written(value=default)


def _written(*, value: Any) -> str:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, enum.Enum):
        return _written(value=value.value)
    if isinstance(value, (str, int, float, Path)):
        return str(value)
    # pydantic-settings reads a compound value as JSON, not as a string: a
    # comma-separated list will not become a list in the field.
    return json.dumps(
        value,
        default=str,
        ensure_ascii=False,
    )
