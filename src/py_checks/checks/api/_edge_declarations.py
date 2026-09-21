"""Вход в процесс объявляет в декораторе всё, что за него решили."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from enum import StrEnum
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, Final, Self

from pydantic import model_validator

from py_checks.checks.api._marker import MARKER
from py_checks.config import OPEN, CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.core import ParsedFile

CODE: Final = "edge-declarations"

STATUS: Final = "status_code"


class Framework(StrEnum):
    """Фреймворк, которым написан вход."""

    FASTAPI = "fastapi"
    FASTSTREAM = "faststream"


@dataclass(frozen=True, slots=True)
class Shape:
    """Как фреймворк записывает вход. Это знание библиотеки, а не проекта.

    Проект решает, что вход обязан объявить; что такое «вход» у FastAPI и у
    FastStream — решено их авторами, и таблица, которую проект писал бы об
    этом, была бы пересказом чужой документации, стареющим вместе с ней.
    """

    # Имена методов, которыми вход объявляют: `broker.subscriber`, `router.post`.
    # Имя объекта слева не читается — это имя переменной, а правило про то, как
    # называют переменную, было бы правилом про орфографию.
    methods: tuple[str, ...]

    # Только декоратором. У маршрута это обязательно: его `methods` — `get`,
    # `post`, `delete`, то есть имена, которыми зовут и клиента HTTP, и правило,
    # читающее любой `.post(...)`, нашло бы маршрут в первом же адаптере к
    # соседнему сервису. Подписку так не спутать ни с чем, а пишут её и
    # декоратором, и вызовом: её держат в переменной и применяют к обработчику
    # отдельно, потому что до старта у неё берут клиента.
    decorated: bool

    # Слово, которым сообщение зовёт первый аргумент.
    subject: str

    # Имя первого аргумента, если он пишется словом; `None` — он позиционный.
    named: str | None

    # Аргумент, объявляющий тело ответа, и статусы, у которых тела не бывает.
    body: str | None = None
    bodiless: tuple[int, ...] = ()

    # Флаг, которым вход говорит, что в схеме его нет.
    exempt: str | None = None


KNOWN: Final[dict[str, Shape]] = {
    Framework.FASTAPI: Shape(
        methods=("get", "post", "put", "patch", "delete", "head", "options", "trace"),
        decorated=True,
        subject="путь",
        named="path",
        body="response_model",
        bodiless=(
            int(HTTPStatus.NO_CONTENT),
            int(HTTPStatus.RESET_CONTENT),
            int(HTTPStatus.NOT_MODIFIED),
        ),
        exempt="include_in_schema",
    ),
    Framework.FASTSTREAM: Shape(
        methods=("subscriber",),
        decorated=False,
        subject="топик",
        named=None,
    ),
}


class Edge(CheckSettings):
    """Что вход этого фреймворка обязан назвать.

    Каждое имя здесь — решение, у которого в библиотеке фреймворка есть
    умолчание, и умолчание это принято не тем, кто пишет сервис.
    """

    required: tuple[str, ...] = ()


class Edges(CheckSettings):
    """Таблица входов: блок на фреймворк.

    ```toml
    [edge-declarations.fastapi]
    required = ["path", "status_code", "summary", "responses"]

    [edge-declarations.faststream]
    required = ["group_id", "parser", "decoder", "ack_policy"]
    ```
    """

    model_config = OPEN
    __pydantic_extra__: dict[str, Edge]  # type: ignore[assignment]

    @model_validator(mode="after")
    def _known(self) -> Self:
        """Имя блока — фреймворк, о котором библиотека что-то знает."""
        unknown = sorted(set(self.frameworks) - set(KNOWN))
        if unknown:
            listed = ", ".join(repr(name) for name in unknown)
            known = ", ".join(sorted(KNOWN))
            message = f"{listed}: про такой фреймворк правило не знает; известны {known}"
            raise ValueError(message)
        return self

    @property
    def frameworks(self) -> dict[str, Edge]:
        return self.__pydantic_extra__


class EdgeDeclarations:
    """Падает, если вход в процесс не сказал, как он себя ведёт.

    Декоратор входа — это контракт. У маршрута его читает тот, кто читает
    сгенерированную схему: соседний сервис, человек, пишущий клиент, — и поле,
    которого в декораторе нет, для него не существует, что бы ни возвращало
    тело функции. У подписки его читает тот, кто разбирается, почему запись
    обработана дважды или не обработана вовсе.

    Механизм у фреймворка есть, требования писать — нет, и каждое умолчание
    там — решение, принятое не этим проектом. Маршрут без `summary` попадёт в
    схему с именем функции вместо описания, а с пустым `responses` — с
    обещанием, что отказов у него не бывает. Подписка без `ack_policy` вернёт
    брокеру запись, которую он только что доставил, а без `auto_offset_reset`
    пропустит то отставание, ради которого новая группа и заводится.

    Что такое вход у FastAPI и у FastStream — знает библиотека: имена методов,
    декоратор это или вызов, как пишется первый аргумент. Проект называет одно:
    что вход обязан объявить.

    Тело объявляется отдельно от прочего и не требуется там, где его не
    бывает: 204, 205 и 304 — это статусы без тела, и модель ответа рядом с
    ними обещает то, что протокол запрещает. Статус, записанный не числом и не
    членом `HTTPStatus`, читается как неизвестный, а неизвестный считается
    имеющим тело: проверка, сработавшая зря, снимается пометкой, а
    промолчавшая — это контракт, которого никто не хватится.

    Вход, выведенный из схемы (`include_in_schema=False`), правило не трогает:
    схема — это то, что оно защищает, а такого маршрута в ней нет.

    Настройки: блок на фреймворк, в нём `required`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = Edges
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        frameworks = settings_as(
            settings=settings,
            model=Edges,
            code=CODE,
        ).frameworks
        decorators = cls._decorators(tree=file.tree)
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.Call):
                continue
            found = cls._matched(
                call=node,
                frameworks=frameworks,
            )
            if found is None:
                continue
            shape, edge = found
            if shape.decorated and node not in decorators:
                continue
            yield from cls._judged(
                call=node,
                file=file,
                shape=shape,
                edge=edge,
            )

    @staticmethod
    def _decorators(*, tree: ast.Module) -> set[ast.Call]:
        """Вызовы, стоящие декоратором: остальное для такого входа — не он."""
        return {
            decorator
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
            for decorator in node.decorator_list
            if isinstance(decorator, ast.Call)
        }

    @staticmethod
    def _matched(
        *,
        call: ast.Call,
        frameworks: dict[str, Edge],
    ) -> tuple[Shape, Edge] | None:
        """Вход какого фреймворка тут объявлен; `None` — не вход."""
        if not isinstance(call.func, ast.Attribute):
            return None
        for name, edge in frameworks.items():
            shape = KNOWN[name]
            if call.func.attr in shape.methods:
                return shape, edge
        return None

    @classmethod
    def _judged(
        cls,
        *,
        call: ast.Call,
        file: ParsedFile,
        shape: Shape,
        edge: Edge,
    ) -> Iterator[Violation]:
        if cls._unpublished(
            call=call,
            exempt=shape.exempt,
        ):
            return
        named = cls._name(
            call=call,
            shape=shape,
        )
        declared = {keyword.arg for keyword in call.keywords}
        yield from cls._first(
            call=call,
            file=file,
            shape=shape,
            named=named,
        )
        for wanted in edge.required:
            # Написанный позиционно там, где так не пишут, уже назван выше;
            # второе замечание о том же входе читается как второй промах.
            if wanted in declared or (wanted == shape.named and call.args):
                continue
            yield cls._violation(
                call=call,
                file=file,
                message=f"{named} не объявляет {wanted}=",
            )
        yield from cls._bodied(
            call=call,
            file=file,
            shape=shape,
            declared=declared,
            named=named,
        )

    @classmethod
    def _first(
        cls,
        *,
        call: ast.Call,
        file: ParsedFile,
        shape: Shape,
        named: str,
    ) -> Iterator[Violation]:
        """Первый аргумент: написан не так, как его пишут, или не написан."""
        if shape.named is not None:
            if call.args:
                yield cls._violation(
                    call=call,
                    file=file,
                    message=f"{named} передаёт {shape.subject} позиционно; напиши {shape.named}=",
                )
            return
        if not call.args:
            yield cls._violation(
                call=call,
                file=file,
                message=f"{named} не называет {shape.subject}; он пишется первым аргументом",
            )

    @classmethod
    def _bodied(
        cls,
        *,
        call: ast.Call,
        file: ParsedFile,
        shape: Shape,
        declared: set[str | None],
        named: str,
    ) -> Iterator[Violation]:
        if shape.body is None or shape.body in declared:
            return
        if cls._status(call=call) in shape.bodiless:
            return
        yield cls._violation(
            call=call,
            file=file,
            message=(
                f"{named} не объявляет {shape.body}= и отвечает телом; "
                f"без него отвечают {', '.join(str(status) for status in shape.bodiless)}"
            ),
        )

    @staticmethod
    def _violation(
        *,
        call: ast.Call,
        file: ParsedFile,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=call,
            path=file.path,
            code=CODE,
            message=message,
        )

    @staticmethod
    def _unpublished(
        *,
        call: ast.Call,
        exempt: str | None,
    ) -> bool:
        """Вход сказал, что в схеме его нет."""
        return exempt is not None and any(
            keyword.arg == exempt
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in call.keywords
        )

    @staticmethod
    def _name(
        *,
        call: ast.Call,
        shape: Shape,
    ) -> str:
        """`POST '/tickets'`, `SUBSCRIBER 'bets.placed'` — как бы ни был записан.

        Предмет объявления читается и из позиции, и из слова: сообщение обязано
        назвать вход и в том файле, где слова как раз нет, — «GET не объявляет
        summary» в модуле с шестью GET не называет ничего.
        """
        attribute = call.func
        method = attribute.attr.upper() if isinstance(attribute, ast.Attribute) else ""
        written = [keyword.value for keyword in call.keywords if keyword.arg == shape.named]
        subject = call.args[:1] + written
        return f"{method} {ast.unparse(subject[0])}" if subject else method

    @staticmethod
    def _status(*, call: ast.Call) -> int | None:
        """Статус, если он записан так, что его видно по файлу."""
        for keyword in call.keywords:
            if keyword.arg != STATUS:
                continue
            match keyword.value:
                case ast.Constant(value=int() as status):
                    return status
                case ast.Attribute(value=ast.Name(id="HTTPStatus"), attr=name):
                    found = getattr(HTTPStatus, name, None)
                    return None if found is None else int(found)
                case _:
                    return None
        return None
