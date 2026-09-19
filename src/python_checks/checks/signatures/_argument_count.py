"""Сколько вход может занимать аргументов."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import Field, model_validator

from python_checks.checks.signatures._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "argument-count"

STATIC: Final = "staticmethod"

type Function = ast.FunctionDef | ast.AsyncFunctionDef


class Subject(CheckSettings):
    """Класс, у которого считают вход, и предел для его методов.

    Класс, а не директория: правило про вход сценария, а рядом с ним в той же
    директории живут хелперы, у которых свои резоны на четыре аргумента.

    `exempt` — методы, чья подпись входом не является. Конструктор в этом
    списке стоит всегда: через него сценарий получает зависимости, а это
    проводка, не вход.
    """

    prefix: str | None = None
    suffix: str | None = None
    max_arguments: int = Field(default=3, gt=0)
    exempt: tuple[str, ...] = ("__init__", "__new__")

    @model_validator(mode="after")
    def _one_subject(self) -> Self:
        if (self.prefix is None) == (self.suffix is None):
            message = "правилу нужен ровно один признак: `prefix` или `suffix`"
            raise ValueError(message)
        return self

    def about(self, *, name: str) -> bool:
        if self.suffix is not None:
            return name.endswith(self.suffix)
        return self.prefix is not None and name.startswith(self.prefix)


class ArgumentCountSettings(CheckSettings):
    subjects: tuple[Subject, ...] = ()


class ArgumentCount:
    """Падает, если вход занимает больше аргументов, чем разрешено.

    Точка входа сценария несёт то, что пришло снаружи, и вход длиннее
    нескольких полей — это вещь с именем: команда, запрос, DTO. Предел
    заставляет эту вещь написать, а не отрастить сценарию ещё один параметр.

    Судится метод класса, названного в таблице, а не всё, что лежит в
    директории: порт или маппер рядом описывает своей подписью, что получает, и
    оборачивать в DTO два порта и метку времени — ничего не купить.

    Первый аргумент метода передаёт интерпретатор, и в счёт он не идёт —
    узнаётся это по месту, а не по имени: `self` в `@staticmethod` считается,
    как и любой другой. `*args` и `**kwargs` считаются по одному.

    Настройка: `subjects`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = ArgumentCountSettings
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(cls, *, file: ParsedFile, settings: CheckSettings) -> Iterator[Violation]:
        subjects = settings_as(settings=settings, model=ArgumentCountSettings, code=CODE).subjects
        if not subjects:
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.ClassDef):
                continue
            subject = next((one for one in subjects if one.about(name=node.name)), None)
            if subject is None:
                continue
            yield from cls._violations(file=file, node=node, subject=subject)

    @classmethod
    def _violations(
        cls,
        *,
        file: ParsedFile,
        node: ast.ClassDef,
        subject: Subject,
    ) -> Iterator[Violation]:
        for method in node.body:
            if not isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            if method.name in subject.exempt:
                continue
            count = cls._count(node=method)
            if count <= subject.max_arguments:
                continue
            yield Violation(
                path=file.path,
                line=method.lineno,
                column=method.col_offset + 1,
                code=CODE,
                message=(
                    f"{node.name}.{method.name} — аргументов {count}, "
                    f"предел {subject.max_arguments}; передай команду, запрос или DTO"
                ),
                # Пометка снимается с любой строки подписи.
                end_line=max(method.body[0].lineno - 1, method.lineno),
            )

    @classmethod
    def _count(cls, *, node: Function) -> int:
        """Всё, что заполняет вызывающий; первый аргумент метода не в счёт."""
        named = [*node.args.posonlyargs, *node.args.args][cls._receiver(node=node) :]
        collectors = [one for one in (node.args.vararg, node.args.kwarg) if one is not None]
        return len(named) + len(node.args.kwonlyargs) + len(collectors)

    @classmethod
    def _receiver(cls, *, node: Function) -> int:
        """Метод получает первый аргумент от интерпретатора, `@staticmethod` — нет."""
        decorators = {cls._decorator(node=item) for item in node.decorator_list}
        return 0 if STATIC in decorators else 1

    @staticmethod
    def _decorator(*, node: ast.expr) -> str:
        match node:
            case ast.Name(id=name) | ast.Attribute(attr=name):
                return name
            case _:
                return ""
