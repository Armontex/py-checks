"""A settings field is named in full: how it arrives and which values are allowed."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from py_checks.checks._location import ZonedSettings, zoned
from py_checks.checks._names import walked
from py_checks.checks.types._marker import MARKER
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.config import CheckSettings
    from py_checks.core import ParsedFile

CODE: Final = "config-fields"

# Classes that hold a vocabulary or an interface, not settings fields.
NOT_SETTINGS: Final[frozenset[str]] = frozenset(
    {"Enum", "StrEnum", "IntEnum", "IntFlag", "Flag", "Protocol", "TypedDict"},
)

# An annotation that says how a value is stored and nothing about which values
# are allowed. Anything else is a name, and a name is a place a rule can live.
BOUNDS: Final[dict[str, tuple[str, ...]]] = {
    "int": ("ge", "gt", "le", "lt"),
    "float": ("ge", "gt", "le", "lt"),
    # `max_length` is left out on purpose: a ceiling says how long a value may
    # be, not that there is one at all — and the point is exactly the empty
    # string an unset variable turns into.
    "str": ("min_length", "pattern"),
}

CLASS_VAR: Final = "ClassVar"

# A field built by a factory is a nested section, not a value: it has no
# variable of its own, the fields inside it read theirs.
FACTORY: Final = "default_factory"


class ConfigFieldsSettings(ZonedSettings):
    factory: str = "Field"
    alias: str | None = None
    bounds: dict[str, tuple[str, ...]] = BOUNDS


class ConfigFields:
    """Fails when a settings field carries no bound.

    The value arrives as text from an environment nobody reviews, so both
    halves of the declaration are compulsory.

    A field is declared through `Field(...)`: that is where the variable's
    alias, the default and the bounds live, and a bare `name: str = "x"`
    silently drops all three.

    A field with a bare number names its bound — `ge`, `gt`, `le`, `lt` — or
    is annotated with a type that carries one. Otherwise
    `POSTGRES_POOL_SIZE=0` and a pool of five hundred are both accepted here
    and fail somewhere the settings are no longer visible in the traceback.

    A bare string is the same hole with a quieter failure: an unset variable
    arrives as an empty string, and an empty broker address, DSN or topic name
    is accepted as configuration. The field names `min_length` or `pattern`,
    or carries a type that does.

    A field names the variable it is read from (`alias`; in pydantic that is
    `validation_alias`). Without it only pydantic knows the variable's name —
    it derives it from the field name and the prefix — and neither the
    `.env.example` built from these same classes nor a person looking for
    where the value comes from can name it. A field built by `default_factory`
    is the exception: it is a nested section, not a value, and the variables
    are read by its own fields.

    A `ClassVar` is not a settings field but a constant next to them.

    Settings: `zones`, `factory`, `alias`, `bounds`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ConfigFieldsSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        limits = settings_as(
            settings=settings,
            model=ConfigFieldsSettings,
            code=CODE,
        )
        where = zoned(
            file=file,
            zones=limits.zones,
        )
        if where is None:
            return
        for node in ast.walk(file.tree):
            if isinstance(node, ast.ClassDef) and cls._settings(node=node):
                yield from cls._fields(
                    file=file,
                    node=node,
                    limits=limits,
                )

    @classmethod
    def _fields(
        cls,
        *,
        file: ParsedFile,
        node: ast.ClassDef,
        limits: ConfigFieldsSettings,
    ) -> Iterator[Violation]:
        for statement in node.body:
            if not isinstance(statement, ast.AnnAssign):
                continue
            if not isinstance(statement.target, ast.Name):
                continue
            named = frozenset(walked(node=statement.annotation))
            if CLASS_VAR in named:
                continue
            reason = cls._reason(
                statement=statement,
                named=named,
                limits=limits,
            )
            if reason is None:
                continue
            yield Violation.from_node(
                node=statement,
                path=file.path,
                code=CODE,
                message=f"{node.name}.{statement.target.id} {reason}",
            )

    @classmethod
    def _reason(
        cls,
        *,
        statement: ast.AnnAssign,
        named: frozenset[str],
        limits: ConfigFieldsSettings,
    ) -> str | None:
        """What the field leaves open, or `None` if nothing."""
        if not cls._declared(
            node=statement.value,
            factory=limits.factory,
        ):
            if statement.value is None:
                return (
                    f"is declared with no value; declare settings fields with {limits.factory}(...)"
                )
            return f"is not declared with {limits.factory}(...)"
        if (
            limits.alias is not None
            and not cls._states(
                node=statement.value,
                wanted=(FACTORY,),
            )
            and not cls._states(
                node=statement.value,
                wanted=(limits.alias,),
            )
        ):
            return (
                f"does not name {limits.alias}=; without it only pydantic knows the "
                f"variable's name, and `.env.example` is built from these same fields"
            )
        wanted = cls._wanted(
            named=named,
            bounds=limits.bounds,
        )
        if wanted and not cls._states(
            node=statement.value,
            wanted=wanted,
        ):
            return (
                f"carries no bound; name one of {', '.join(wanted)} "
                f"or annotate it with a type that carries the rule"
            )
        return None

    @staticmethod
    def _wanted(
        *,
        named: frozenset[str],
        bounds: dict[str, tuple[str, ...]],
    ) -> tuple[str, ...]:
        """Which bounds the annotation owes.

        `str | None` is a string and `int | None` is a number: the union says
        whether there is a value, not which values are allowed. A name not in
        the table is already a rule: the bound lives in it.
        """
        if not named or not named <= frozenset(bounds):
            return ()
        listed = [one for name in sorted(named) for one in bounds[name]]
        return tuple(dict.fromkeys(listed))

    @staticmethod
    def _declared(
        *,
        node: ast.expr | None,
        factory: str,
    ) -> bool:
        match node:
            case ast.Call(func=ast.Name(id=name) | ast.Attribute(attr=name)):
                return name == factory
            case _:
                return False

    @staticmethod
    def _states(
        *,
        node: ast.expr | None,
        wanted: tuple[str, ...],
    ) -> bool:
        if not isinstance(node, ast.Call):
            return False
        return any(keyword.arg in wanted for keyword in node.keywords)

    @staticmethod
    def _settings(*, node: ast.ClassDef) -> bool:
        """A class of settings fields, not a vocabulary or an interface beside them."""
        bases = {
            base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", "")
            for base in node.bases
        }
        return not bases & NOT_SETTINGS
