"""Запрос называет колонку атрибутом, а не строкой, и ходит в базу один раз."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from python_checks.checks._location import place
from python_checks.checks.database._marker import MARKER
from python_checks.config import CheckSettings
from python_checks.core import Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from python_checks.core import ParsedFile

CODE: Final = "statement-keys"

SAID: Final = "называет колонку строкой; маппед-атрибут переезжает вместе с ней"


class StatementKeysSettings(CheckSettings):
    zones: tuple[str, ...] = ()
    lists: tuple[str, ...] = ("index_elements",)
    mappings: tuple[str, ...] = ("set_",)
    calls: tuple[str, ...] = ("from_select",)
    loops: tuple[str, ...] = ("execute",)


class StatementKeys:
    """Падает, если запрос называет колонку строкой или ходит в базу в цикле.

    Строки собираются через модели, поэтому список колонок держит pyright:
    пропущенная колонка — пропущенный аргумент, переименованная — неожиданное
    ключевое слово. Строковый ключ в `index_elements=[...]`, `set_={...}` или
    `from_select` открывает дыру заново: он ничего не совпадает во время
    проверки и либо падает, либо молча перестаёт совпадать на той строке, что
    выполняется.

    `index_elements` и `set_` вместе — это `ON CONFLICT DO UPDATE`, то есть
    inbox и каждый upsert. Строка, переставшая там совпадать, не поднимает
    исключения: конфликт просто не находится, дубль вставляется второй раз, и
    идемпотентность — то, ради чего inbox и существует, — тихо кончается.

    Второе правило: `execute(...)` внутри цикла — это поход в базу на итерацию,
    форма N+1. Сто ставок — сто поездок туда и обратно там, где хватило бы
    одного запроса по всему множеству. Иногда цикл честен — три константы, и
    одного запроса, говорящего то же самое, не существует, — поэтому правило
    снимается пометкой на строке цикла или самого вызова, а не отсутствует.

    Настройки: `zones`, `lists`, `mappings`, `calls`, `loops`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = StatementKeysSettings
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
            model=StatementKeysSettings,
            code=CODE,
        )
        where = place(file=file)
        if where is None or not any(where.holds(path=zone) for zone in limits.zones):
            return
        for node in ast.walk(file.tree):
            if isinstance(node, ast.Call):
                yield from cls._keys(
                    file=file,
                    node=node,
                    limits=limits,
                )
            if isinstance(node, ast.For | ast.AsyncFor | ast.While):
                yield from cls._loop(
                    file=file,
                    node=node,
                    limits=limits,
                )

    @classmethod
    def _keys(
        cls,
        *,
        file: ParsedFile,
        node: ast.Call,
        limits: StatementKeysSettings,
    ) -> Iterator[Violation]:
        for keyword in node.keywords:
            if keyword.arg in limits.lists:
                yield from cls._strings(
                    file=file,
                    written=keyword.arg,
                    nodes=cls._elements(node=keyword.value),
                )
            if keyword.arg in limits.mappings:
                yield from cls._strings(
                    file=file,
                    written=keyword.arg,
                    nodes=cls._keyed(node=keyword.value),
                )
        if cls._name(node=node.func) in limits.calls and node.args:
            yield from cls._strings(
                file=file,
                written=cls._name(node=node.func),
                nodes=cls._elements(node=node.args[0]),
            )

    @classmethod
    def _loop(
        cls,
        *,
        file: ParsedFile,
        node: ast.For | ast.AsyncFor | ast.While,
        limits: StatementKeysSettings,
    ) -> Iterator[Violation]:
        """Поход в базу на каждой итерации."""
        for child in ast.walk(node):
            if not isinstance(child, ast.Call) or cls._name(node=child.func) not in limits.loops:
                continue
            yield Violation(
                path=file.path,
                line=node.lineno,
                column=node.col_offset + 1,
                code=CODE,
                # Пометка снимается со строки цикла или с любой строки вызова:
                # причина принадлежит тому месту, где автор её и пишет.
                end_line=child.end_lineno or child.lineno,
                message=(
                    f"{cls._name(node=child.func)}() внутри цикла — поход в базу на итерацию; "
                    f"один запрос по всему множеству говорит то же самое"
                ),
            )

    @classmethod
    def _strings(
        cls,
        *,
        file: ParsedFile,
        written: str,
        nodes: Iterator[ast.expr],
    ) -> Iterator[Violation]:
        for node in nodes:
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            yield Violation.from_node(
                node=node,
                path=file.path,
                code=CODE,
                message=f"{written}: {SAID}",
            )

    @staticmethod
    def _elements(*, node: ast.expr) -> Iterator[ast.expr]:
        if isinstance(node, ast.List | ast.Tuple | ast.Set):
            yield from node.elts

    @staticmethod
    def _keyed(*, node: ast.expr) -> Iterator[ast.expr]:
        if isinstance(node, ast.Dict):
            yield from (key for key in node.keys if key is not None)

    @staticmethod
    def _name(*, node: ast.expr) -> str:
        match node:
            case ast.Name(id=name) | ast.Attribute(attr=name):
                return name
            case _:
                return ""
