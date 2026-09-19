"""Операция — один класс, одна дверь и ничего рядом."""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING, ClassVar, Final

from pydantic import Field

from py_checks.checks._kind import Kind, declarations
from py_checks.checks._location import place
from py_checks.checks.placement._marker import MARKER
from py_checks.config import CheckSettings
from py_checks.core import Scope, Violation, settings_as

if TYPE_CHECKING:
    from collections.abc import Iterator

    from py_checks.checks._kind import Declaration
    from py_checks.core import ParsedFile

CODE: Final = "operation-shape"

PRIVATE: Final = "_"

STATIC: Final = "staticmethod"


class Operation(CheckSettings):
    """Директория с операциями и форма, которую там держат.

    `method` — единственная публичная дверь: сценарий просят об одном деле, и
    второй публичный метод означает вторую операцию, поделившую с первой
    конструктор. Пусто — значит число дверей не ограничено: у сервиса модуля
    их столько, сколько переходов у его сущности, и это тот же выбор, а не
    поблажка.

    `forbids` — имена типов, которых операция не держит: `UnitOfWork` ловится
    и как `IPlacementUnitOfWork`, и как `UnitOfWorkFactory`, потому что
    запрещено держать транзакцию, а не писать её имя одним конкретным образом.

    `max_arguments` — сколько аргументов занимает вход. Дверь несёт то, что
    пришло снаружи, и вход длиннее нескольких полей — вещь с именем: команда,
    запрос, DTO. Считаются публичные методы: конструктор получает зависимости,
    а это проводка, не вход, и в счёт он не идёт уже потому, что публичным не
    является.
    """

    inside: str
    suffix: str
    method: str | None = None
    forbids: tuple[str, ...] = ()
    max_arguments: int | None = Field(
        default=None,
        gt=0,
    )


class OperationShapeSettings(CheckSettings):
    operations: tuple[Operation, ...] = ()


class OperationShape:
    """Падает, если операция устроена не как операция.

    Вход двери ограничен по числу аргументов, если предел задан: то, что
    пришло снаружи, длиннее нескольких полей — это команда, запрос или DTO.

    Рядом с операцией не стоит ничего: ни второй класс, ни функция — ни выше,
    ни ниже. Хелпер перед предметом — абзац, который читатель пролистывает;
    хелпер после — тот же хелпер, ничем не разделяемый: нужен операции — стал
    приватным методом, нужен двоим — переехал туда, где лежит общее.

    Константы и алиасы стоять могут: имя читают там, где им пользуются.
    Перечисление — не может, в отличие от других директорий: словарь — это
    класс, и операция, которой он понадобился, называет то, чем её модуль не
    владеет.

    `__init__.py`, пустой модуль и модуль с подчёркиванием правилу не подсудны.
    Модуль, не объявивший операции вовсе, — тоже: об этом говорит
    `required-class`, и второе мнение сообщило бы одну ошибку дважды.

    Настройка: `operations`.
    """

    code: ClassVar[str] = CODE
    Settings: ClassVar[type[CheckSettings]] = OperationShapeSettings
    scope: ClassVar[Scope] = Scope.FILE
    marker: ClassVar[str] = MARKER

    @classmethod
    def run(
        cls,
        *,
        file: ParsedFile,
        settings: CheckSettings,
    ) -> Iterator[Violation]:
        listed = settings_as(
            settings=settings,
            model=OperationShapeSettings,
            code=CODE,
        ).operations
        where = place(file=file)
        if where is None or file.path.stem.startswith(PRIVATE):
            return
        matched = [
            (depth, len(one.inside), one)
            for one in listed
            if (depth := where.within(directory=one.inside)) is not None
        ]
        if not matched:
            return
        rule = max(matched, key=lambda found: found[:2])[2]
        declared = list(declarations(tree=file.tree))
        subject = cls._subject(
            declared=declared,
            rule=rule,
        )
        found = list(
            cls._beside(
                file=file,
                declared=declared,
                subject=subject,
                rule=rule,
            )
        )
        if subject is not None and isinstance(subject.node, ast.ClassDef):
            found += [
                *cls._door(
                    file=file,
                    subject=subject,
                    node=subject.node,
                    rule=rule,
                ),
                *cls._input(
                    file=file,
                    subject=subject,
                    node=subject.node,
                    rule=rule,
                ),
                *cls._held(
                    file=file,
                    subject=subject,
                    node=subject.node,
                    rule=rule,
                ),
            ]
        yield from sorted(found, key=lambda violation: (violation.line, violation.column))

    @staticmethod
    def _subject(
        *,
        declared: list[Declaration],
        rule: Operation,
    ) -> Declaration | None:
        """Операция, ради которой существует модуль, — по имени, а не по месту.

        По месту было бы неверно: класс, по ошибке вставший выше операции, —
        то самое, о чём правило и сообщает, — оказался бы предметом, и модуль
        услышал бы, что у его словаря нет `execute()`. Одна ошибка — одна
        жалоба.
        """
        classes = [one for one in declared if isinstance(one.node, ast.ClassDef)]
        named = [one for one in classes if one.name.endswith(rule.suffix)]
        return next(iter(named or classes), None)

    @classmethod
    def _beside(
        cls,
        *,
        file: ParsedFile,
        declared: list[Declaration],
        subject: Declaration | None,
        rule: Operation,
    ) -> Iterator[Violation]:
        """Всё, что встало рядом с операцией: второй класс или функция."""
        for one in declared:
            if one.kind is Kind.ALIAS or one is subject:
                continue
            if one.kind is Kind.FUNCTION:
                yield cls._says(
                    file=file,
                    declared=one,
                    message=(
                        f"{one.name}() стоит рядом с операцией; нужный ей хелпер — "
                        f"приватный метод, нужный двоим — общий код"
                    ),
                )
                continue
            yield cls._says(
                file=file,
                declared=one,
                message=(
                    f"{one.name} стоит рядом с операцией; в {rule.inside} модуль "
                    f"объявляет один класс и больше ничего"
                ),
            )

    @classmethod
    def _door(
        cls,
        *,
        file: ParsedFile,
        subject: Declaration,
        node: ast.ClassDef,
        rule: Operation,
    ) -> Iterator[Violation]:
        """Единственная публичная дверь операции."""
        if rule.method is None:
            return
        public = cls._public(node=node)
        names = [method.name for method in public]
        if names == [rule.method]:
            return
        if not public:
            yield cls._says(
                file=file,
                declared=subject,
                message=(
                    f"у {subject.name} нет публичного метода; об операции просят "
                    f"одним, и он называется {rule.method}()"
                ),
            )
            return
        yield Violation.from_node(
            node=public[0],
            path=file.path,
            code=CODE,
            message=(
                f"{subject.name} предлагает {', '.join(f'{name}()' for name in names)}; "
                f"у операции один публичный метод, и это {rule.method}() — "
                f"остальные приватны или это другой класс"
            ),
        )

    @classmethod
    def _input(
        cls,
        *,
        file: ParsedFile,
        subject: Declaration,
        node: ast.ClassDef,
        rule: Operation,
    ) -> Iterator[Violation]:
        """Сколько аргументов занимает вход."""
        if rule.max_arguments is None:
            return
        for method in cls._public(node=node):
            count = cls._arguments(node=method)
            if count <= rule.max_arguments:
                continue
            yield Violation.from_node(
                node=method,
                path=file.path,
                code=CODE,
                message=(
                    f"{subject.name}.{method.name} — аргументов {count}, предел "
                    f"{rule.max_arguments}; передай команду, запрос или DTO"
                ),
                # Пометка снимается с любой строки подписи.
                end_line=max(method.body[0].lineno - 1, method.lineno),
            )

    @classmethod
    def _arguments(cls, *, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Всё, что заполняет вызывающий; первый аргумент метода не в счёт.

        По месту, а не по имени: `self` в `@staticmethod` — обычный аргумент.
        """
        receiver = 0 if cls._static(node=node) else 1
        named = [*node.args.posonlyargs, *node.args.args][receiver:]
        collectors = [one for one in (node.args.vararg, node.args.kwarg) if one is not None]
        return len(named) + len(node.args.kwonlyargs) + len(collectors)

    @staticmethod
    def _static(*, node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        names = {
            item.id if isinstance(item, ast.Name) else getattr(item, "attr", "")
            for item in node.decorator_list
        }
        return STATIC in names

    @classmethod
    def _held(
        cls,
        *,
        file: ParsedFile,
        subject: Declaration,
        node: ast.ClassDef,
        rule: Operation,
    ) -> Iterator[Violation]:
        """Тип, которого операция не держит, — в поле или в параметре."""
        for annotation in cls._annotations(node=node):
            held = next(
                (
                    name
                    for name in cls._typed(node=annotation)
                    for mark in rule.forbids
                    if mark in name
                ),
                None,
            )
            if held is None:
                continue
            yield Violation.from_node(
                node=annotation,
                path=file.path,
                code=CODE,
                message=(
                    f"{subject.name} держит {held}; операции передают то, через что "
                    f"она пишет, а транзакция остаётся вызывающему"
                ),
            )

    @staticmethod
    def _public(*, node: ast.ClassDef) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
        """Методы, до которых может дотянуться вызывающий, в порядке объявления.

        `@property` считается: это то, что с операции читают, а предложить ей
        нечего, кроме одного.
        """
        return [
            statement
            for statement in node.body
            if isinstance(statement, ast.FunctionDef | ast.AsyncFunctionDef)
            and not statement.name.startswith(PRIVATE)
        ]

    @staticmethod
    def _annotations(*, node: ast.ClassDef) -> Iterator[ast.expr]:
        """Всё, что класс объявил аннотацией: поля и параметры методов."""
        for child in ast.walk(node):
            match child:
                case ast.AnnAssign(annotation=annotation):
                    yield annotation
                case ast.arg(annotation=ast.expr() as annotation):
                    yield annotation
                case _:
                    continue

    @staticmethod
    def _typed(*, node: ast.expr) -> Iterator[str]:
        """Имена типов, написанные внутри аннотации."""
        for child in ast.walk(node):
            match child:
                case ast.Name(id=name) | ast.Attribute(attr=name):
                    yield name
                # Отложенная ссылка `uow: "PlacementUnitOfWork"` — та же
                # зависимость, записанная ради проверяльщика типов.
                case ast.Constant(value=str() as text):
                    yield text
                case _:
                    continue

    @staticmethod
    def _says(
        *,
        file: ParsedFile,
        declared: Declaration,
        message: str,
    ) -> Violation:
        return Violation.from_node(
            node=declared.node,
            path=file.path,
            code=CODE,
            message=message,
        )
