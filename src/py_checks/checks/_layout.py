"""The project's layout: one block per directory.

Four rules speak of the same thing from four sides: what may lie here
(`class-modules`), what lives only here (`class-placement`), what a module must
declare (`required-class`) and what shape an operation has here
(`operation-shape`). Each used to have a table of its own, and one fact about
`use_cases` had to be written four times in four syntaxes, stitched together
by eye on a string key.

Now there is one block per directory, and the rules read their own columns
from it:

```toml
[layout."application/use_cases"]
only = ["class"]
suffix = "UseCase"
required = true
operation = { method = "execute", max-arguments = 3 }
```

The rules still know nothing of each other — they simply read one table. The
address in the heading is looked for as consecutive path parts, so
`application/use_cases` is found in a modular service too, where the path
starts with `modules/<name>/`, and `*` matches any one part.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Final, Self

from pydantic import Field, model_validator

from py_checks.checks._kind import Kind
from py_checks.config import CheckSettings

if TYPE_CHECKING:
    from collections.abc import Iterable

    from py_checks.checks._kind import Declaration
    from py_checks.checks._location import Place

SECTION: Final = "layout"


class Orm(StrEnum):
    """What a directory is to an ORM model.

    The model's home and the place where it is built are two ends of one
    convention, and writing them in a separate table would name the same two
    directories a second time: the layout already knows them by name.
    """

    # Models are declared here: anywhere else it is a table nobody expects at
    # that address, and alembic's autogenerate sees only their package.
    DECLARED = "declared"

    # Models are built here: building a model means writing a row.
    BUILT = "built"


class Operation(CheckSettings):
    """The shape of an operation kept in this directory.

    `method` is the only public door: a use case is asked for one thing, and a
    second public method means a second operation sharing a constructor with
    the first. Empty means the number of doors is not limited: a module's
    service has as many as its entity has transitions.

    `forbids` is the names of types an operation does not hold: `UnitOfWork` is
    caught both as `IPlacementUnitOfWork` and as `UnitOfWorkFactory`, because
    what is forbidden is holding the transaction, not spelling its name one
    particular way.

    `max_arguments` is how many arguments the entrance takes. A door carries
    what came from outside, and an entrance longer than a few fields is a thing
    with a name: a command, a query, a DTO.
    """

    method: str | None = None
    forbids: tuple[str, ...] = ()
    max_arguments: int | None = Field(
        default=None,
        gt=0,
    )


class Directory(CheckSettings):
    """What the project keeps in this directory.

    `only` — the kinds that belong here, and nothing else sits beside them.
    `home` — the kinds that belong ONLY here: a port declared at the other end
    of the tree is a port the reader will not find.
    `area` — the part of the tree within which home and name mean anything at
    all: the rule about `dto` is written about the application layer, and a
    dataclass in the bootstrap or in observability is just a way to put three
    fields side by side.
    `suffix` — what the class this directory exists for is called; it too
    lives only here.
    `required` — a module must declare such a class, first and alone.
    `operation` — the shape of an operation, if operations are kept here.
    `orm` — what the directory is to an ORM model: its home or where it is built.
    `base` — the base class by which a model is recognised in the models' home.
    """

    only: tuple[Kind, ...] = ()
    home: tuple[Kind, ...] = ()
    area: str | None = None
    suffix: str | None = None
    required: bool = False
    operation: Operation | None = None
    orm: Orm | None = None
    base: str | None = None

    @model_validator(mode="after")
    def _named(self) -> Self:
        """Obligation and shape rest on the name: without a suffix there is no checking them."""
        if self.suffix is not None:
            return self
        if self.required:
            message = "`required` without `suffix`: it is unclear which class must be there"
            raise ValueError(message)
        if self.operation is not None:
            message = (
                "`operation` without `suffix`: it is unclear which class is the operation here"
            )
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _claims(self) -> Self:
        """An area narrows a claim: without a home and a name there is nothing to narrow."""
        if self.area is not None and not self.home and self.suffix is None:
            message = "`area` without `home` and `suffix`: this directory claims nothing"
            raise ValueError(message)
        return self

    @model_validator(mode="after")
    def _declares(self) -> Self:
        """`base` is about the models' home: where they are built, there is nothing to spot."""
        if self.base is not None and self.orm is not Orm.DECLARED:
            message = '`base` without `orm = "declared"`: the base is named by the models\' home'
            raise ValueError(message)
        return self


class Layout(CheckSettings):
    """The `[layout]` section: a directory's address — and a block about it.

    The keys come from the project, so the model accepts any: directory names
    are data, not fields. What is checked is the content of the block.
    """

    model_config = CheckSettings.model_config | {"extra": "allow"}

    # pydantic's typed `extra`: the key is an address, the value a block.
    __pydantic_extra__: dict[str, Directory]  # type: ignore[assignment]

    @property
    def directories(self) -> dict[str, Directory]:
        return self.__pydantic_extra__


def addressed(
    *,
    layout: dict[str, Directory],
    orm: Orm,
) -> tuple[str, ...]:
    """The addresses that declared themselves this end of the ORM model convention."""
    return tuple(address for address, directory in layout.items() if directory.orm is orm)


def innermost(
    *,
    where: Place,
    among: Iterable[tuple[str, Directory]],
) -> tuple[str, Directory] | None:
    """The block of the innermost matched directory.

    The deepest wins: `modules/betslip/application/services` beats
    `application`. At equal depth, the longer address: a path says more about a
    place than one name.
    """
    matched = [
        (depth, len(address), address, directory)
        for address, directory in among
        if (depth := where.within(directory=address)) is not None
    ]
    if not matched:
        return None
    deepest = max(matched, key=lambda found: found[:2])
    return deepest[2], deepest[3]


@dataclass(frozen=True, slots=True)
class Claim:
    """Whose home this is and why the declaration asks to be in it."""

    address: str
    said: str


def claimants(
    *,
    declared: Declaration,
    layout: dict[str, Directory],
    where: Place,
) -> list[Claim]:
    """The addresses that claim this declaration: by name or by kind.

    A block with `area` claims only what lies inside the named part of the
    tree: the convention about `dto` is written about the application layer,
    and a dataclass in the bootstrap is not its to judge.
    """
    found: list[Claim] = []
    for address, directory in layout.items():
        if directory.area is not None and not where.holds(path=directory.area):
            continue
        said = _claim(
            declared=declared,
            directory=directory,
        )
        if said is not None:
            found.append(
                Claim(
                    address=address,
                    said=said,
                )
            )
    return found


def _claim(
    *,
    declared: Declaration,
    directory: Directory,
) -> str | None:
    """Why this address claims the declaration; `None` — it does not."""
    if directory.suffix is not None and declared.name.endswith(directory.suffix):
        return f"ends with {directory.suffix}"
    if declared.kind is not None and declared.kind in directory.home:
        return f"— {declared.kind.said}"
    return None
