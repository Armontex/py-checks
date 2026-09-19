"""Маршрут объявляет в декораторе всё, чем он будет описан в схеме."""

from __future__ import annotations

import ast
from http import HTTPStatus
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks.api._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "endpoint-declarations"

PATH: Final = "path"
STATUS: Final = "status_code"


class EndpointDeclarationsSettings(CheckSettings):
    methods: tuple[str, ...] = ()
    required: tuple[str, ...] = ()
    body: str | None = None
    bodiless: tuple[int, ...] = ()
    exempt: str | None = None


class EndpointDeclarations:
    """Падает, если маршрут не сказал, чем он отвечает.

    Декоратор маршрута — это контракт. Кто читает сгенерированную схему —
    соседний сервис, человек, пишущий клиент, — читает только то, что объявил
    декоратор, и поле, которого там нет, для него не существует, что бы ни
    возвращало тело функции.

    Механизм у фреймворка есть, требования писать — нет. Маршрут без `summary`
    попадёт в схему с именем функции вместо описания, а с пустым `responses` —
    с обещанием, что отказов у него не бывает: успех из подписи выводится,
    отказы — нет, и ничто в ней не говорит, что этот маршрут отвечает 409.

    Путь пишется словом `path=`: позиционный первый аргумент — единственное в
    декораторе, чей смысл зависит от позиции.

    Тело объявляется отдельно от прочего и не требуется там, где его не
    бывает: 204, 205 и 304 — это статусы без тела, и модель ответа рядом с
    ними обещает то, что протокол запрещает. Статус, записанный не числом и не
    членом `HTTPStatus`, читается как неизвестный, а неизвестный считается
    имеющим тело: проверка, сработавшая зря, снимается пометкой, а
    промолчавшая — это контракт, которого никто не хватится.

    Маршрут, выведенный из схемы (`include_in_schema=False`), правило не
    трогает: схема — это то, что оно защищает, а такого маршрута в ней нет.

    Настройки: `methods`, `required`, `body`, `bodiless`, `exempt`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = EndpointDeclarationsSettings
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
            model=EndpointDeclarationsSettings,
            code=CODE,
        )
        if not limits.methods:
            return
        for node in ast.walk(file.tree):
            if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not cls._route(
                    node=decorator,
                    methods=limits.methods,
                ):
                    continue
                yield from cls._judged(
                    route=decorator,
                    file=file,
                    limits=limits,
                )

    @classmethod
    def _judged(
        cls,
        *,
        route: ast.Call,
        file: ParsedFile,
        limits: EndpointDeclarationsSettings,
    ) -> Iterator[Violation]:
        if cls._unpublished(
            route=route,
            exempt=limits.exempt,
        ):
            return
        named = cls._name(route=route)
        declared = {keyword.arg for keyword in route.keywords}
        if route.args:
            yield cls._violation(
                route=route,
                file=file,
                message=f"{named} передаёт путь позиционно; напиши {PATH}=",
            )
        for wanted in limits.required:
            if wanted in declared or (wanted == PATH and route.args):
                continue
            yield cls._violation(
                route=route,
                file=file,
                message=f"{named} не объявляет {wanted}=",
            )
        if limits.body is None or limits.body in declared:
            return
        if cls._status(route=route) in limits.bodiless:
            return
        yield cls._violation(
            route=route,
            file=file,
            message=(
                f"{named} не объявляет {limits.body}= и отвечает телом; "
                f"без него отвечают {', '.join(str(status) for status in limits.bodiless)}"
            ),
        )

    @staticmethod
    def _violation(
        *,
        route: ast.Call,
        file: ParsedFile,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=route,
            path=file.path,
            code=CODE,
            message=message,
        )

    @staticmethod
    def _route(
        *,
        node: ast.Call,
        methods: tuple[str, ...],
    ) -> bool:
        """Декоратор вида `<что-то>.<метод>(...)`, а не `@app.middleware(...)`."""
        return isinstance(node.func, ast.Attribute) and node.func.attr in methods

    @staticmethod
    def _unpublished(
        *,
        route: ast.Call,
        exempt: str | None,
    ) -> bool:
        """Маршрут сказал, что в схеме его нет."""
        return exempt is not None and any(
            keyword.arg == exempt
            and isinstance(keyword.value, ast.Constant)
            and keyword.value.value is False
            for keyword in route.keywords
        )

    @staticmethod
    def _name(*, route: ast.Call) -> str:
        """`POST '/tickets'` — как бы путь ни был записан.

        Путь читается и из слова, и из первого аргумента: сообщение обязано
        назвать маршрут и в том файле, где слова как раз нет, — «GET не
        объявляет summary» в модуле с шестью GET не называет ничего.
        """
        attribute = route.func
        method = attribute.attr.upper() if isinstance(attribute, ast.Attribute) else ""
        written = [keyword.value for keyword in route.keywords if keyword.arg == PATH]
        path = route.args[:1] + written
        return f"{method} {ast.unparse(path[0])}" if path else method

    @staticmethod
    def _status(*, route: ast.Call) -> int | None:
        """Статус, если он записан так, что его видно по файлу."""
        for keyword in route.keywords:
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
